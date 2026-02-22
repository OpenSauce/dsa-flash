import logging
import re
from datetime import datetime, timezone
from pathlib import Path

import yaml
from sqlmodel import Session, select

from .database import engine
from .models import Flashcard, Lesson, Quiz, QuizQuestion

logger = logging.getLogger(__name__)

ROOT = Path("/data/flashcards")  # mounted via compose


def _dir_metadata(path: Path) -> tuple[str | None, str | None]:
    """
    Derive (category, language) from .../category/(language/)?file.yaml
    """
    parts = path.parent.relative_to(ROOT).parts
    if len(parts) == 1:
        return parts[0], None
    if len(parts) >= 2:
        return parts[0], parts[1]
    return None, None


def upsert_flashcard(card: Flashcard, session: Session) -> None:
    """
    Insert or update by (title, category, language) composite key.
    """
    stmt = select(Flashcard).where(
        Flashcard.title == card.title,
        Flashcard.category == card.category,
        Flashcard.language == card.language,
    )
    exists = session.exec(stmt).first()
    if exists:
        exists.front = card.front
        exists.back = card.back
        exists.difficulty = card.difficulty
        exists.tags = card.tags
        exists.lesson_slug = card.lesson_slug
    else:
        session.add(card)


def load_yaml_flashcards() -> None:
    """
    Walk every *.yml / *.yaml under ROOT and upsert cards.
    Skips .github/ directory and .yamllint.yml file.
    After upserting, removes any DB cards no longer present in YAML.
    """
    yaml_paths = list(ROOT.rglob("*.yml")) + list(ROOT.rglob("*.yaml"))

    # Track all (title, category, language) tuples from YAML
    yaml_keys: set[tuple[str, str | None, str | None]] = set()

    with Session(engine) as session:
        for file in yaml_paths:
            # Skip .yamllint.yml
            if file.name == ".yamllint.yml":
                continue
            # Skip any file under a .github/ directory
            if ".github" in file.parts:
                continue

            category, language = _dir_metadata(file)
            if category is not None:
                category = category.replace(" ", "-")
            data = yaml.safe_load(file.read_text()) or []
            if not isinstance(data, list):
                logger.warning("Skipping %s: root is %s, not list", file, type(data).__name__)
                continue
            for raw in data:
                card = Flashcard(
                    title=raw["title"],
                    front=raw["Front"],
                    back=raw["Back"],
                    difficulty=raw.get("difficulty"),
                    tags=raw.get("tags") or [],
                    category=category,
                    language=language,
                    lesson_slug=raw.get("lesson"),
                )
                upsert_flashcard(card, session)
                yaml_keys.add((raw["title"], category, language))

        # Remove cards from DB that are no longer in YAML
        all_db_cards = session.exec(select(Flashcard)).all()
        orphans = [
            db_card
            for db_card in all_db_cards
            if (db_card.title, db_card.category, db_card.language) not in yaml_keys
        ]

        total = len(all_db_cards)
        orphan_count = len(orphans)
        if total > 0 and orphan_count > total * 0.5:
            logger.warning(
                "Orphan removal aborted: %d of %d cards would be deleted (%.0f%%). "
                "This likely means the YAML submodule is not mounted or a directory was renamed. "
                "Fix the mount and restart to apply removals.",
                orphan_count,
                total,
                100 * orphan_count / total,
            )
        else:
            for db_card in orphans:
                logger.info(
                    "Removing orphaned card: %s (%s/%s)",
                    db_card.title,
                    db_card.category,
                    db_card.language,
                )
                session.delete(db_card)

        session.commit()


def _parse_front_matter(text: str) -> tuple[dict, str]:
    """Split YAML front matter from markdown body."""
    match = re.match(r'^---\s*\n(.*?)\n---\s*\n(.*)', text, re.DOTALL)
    if not match:
        return {}, text
    front_matter = yaml.safe_load(match.group(1)) or {}
    body = match.group(2)
    return front_matter, body


def _estimate_reading_time(text: str) -> int:
    """Estimate reading time in minutes (~200 words/min, minimum 1)."""
    words = len(text.split())
    return max(1, round(words / 200))


def upsert_lesson(lesson: Lesson, session: Session) -> None:
    """Insert or update by slug."""
    existing = session.exec(
        select(Lesson).where(Lesson.slug == lesson.slug)
    ).first()
    if existing:
        existing.title = lesson.title
        existing.category = lesson.category
        existing.order = lesson.order
        existing.content = lesson.content
        existing.summary = lesson.summary
        existing.reading_time_minutes = lesson.reading_time_minutes
        existing.updated_at = datetime.now(timezone.utc)
    else:
        session.add(lesson)


def load_lessons() -> None:
    """Walk {category}/lessons/*.md under ROOT and upsert lessons."""
    lesson_files = list(ROOT.rglob("lessons/*.md"))
    yaml_slugs: set[str] = set()

    with Session(engine) as session:
        for file in lesson_files:
            # Skip .github directory
            if ".github" in file.parts:
                continue

            # Derive category from path: ROOT/{category}/lessons/{slug}.md
            rel = file.relative_to(ROOT)
            parts = rel.parts  # e.g., ("docker", "lessons", "docker-layers.md")
            if len(parts) < 3 or parts[-2] != "lessons":
                continue
            category = parts[0].replace(" ", "-")
            slug = file.stem  # filename without .md

            text = file.read_text()
            front_matter, body = _parse_front_matter(text)

            lesson = Lesson(
                title=front_matter.get("title", slug.replace("-", " ").title()),
                slug=slug,
                category=category,
                order=front_matter.get("order", 0),
                content=body.strip(),
                summary=front_matter.get("summary", ""),
                reading_time_minutes=_estimate_reading_time(body),
            )
            upsert_lesson(lesson, session)
            yaml_slugs.add(slug)

        # Remove orphan lessons no longer in files
        all_db_lessons = session.exec(select(Lesson)).all()
        orphans = [ls for ls in all_db_lessons if ls.slug not in yaml_slugs]
        if len(orphans) > len(all_db_lessons) * 0.5:
            logger.warning(
                "Skipping orphan removal: %d of %d lessons would be deleted (>50%%)",
                len(orphans),
                len(all_db_lessons),
            )
        else:
            for lesson in orphans:
                logger.info("Removing orphaned lesson: %s", lesson.slug)
                session.delete(lesson)

        session.commit()


def upsert_quiz(quiz: Quiz, raw_questions: list[dict], session: Session) -> None:
    """Insert or update quiz by slug, then sync questions (delete + reinsert)."""
    existing = session.exec(
        select(Quiz).where(Quiz.slug == quiz.slug)
    ).first()
    if existing:
        existing.title = quiz.title
        existing.category = quiz.category
        existing.lesson_slug = quiz.lesson_slug
        existing.updated_at = datetime.now(timezone.utc)
        quiz_obj = existing
    else:
        session.add(quiz)
        session.flush()
        quiz_obj = quiz

    # Delete existing questions and reinsert
    old_questions = session.exec(
        select(QuizQuestion).where(QuizQuestion.quiz_id == quiz_obj.id)
    ).all()
    for q in old_questions:
        session.delete(q)
    session.flush()

    for i, raw_q in enumerate(raw_questions):
        options = raw_q.get("options", [])
        correct = raw_q.get("correct", 0)
        if not isinstance(options, list) or len(options) != 4:
            logger.warning(
                "Quiz %s question %d skipped: expected 4 options, got %s",
                quiz.slug,
                i,
                len(options) if isinstance(options, list) else type(options).__name__,
            )
            continue
        if not isinstance(correct, int) or correct < 0 or correct >= len(options):
            logger.warning(
                "Quiz %s question %d skipped: correct index %s out of range",
                quiz.slug,
                i,
                correct,
            )
            continue
        question_text = raw_q.get("question", "")
        if not question_text:
            logger.warning("Quiz %s question %d skipped: missing question text", quiz.slug, i)
            continue
        qq = QuizQuestion(
            quiz_id=quiz_obj.id,
            order=i,
            question=question_text,
            options=options,
            correct_index=correct,
            explanation=raw_q.get("explanation", ""),
        )
        session.add(qq)


def load_quizzes() -> None:
    """Walk {category}/quizzes/*.yaml under ROOT and upsert quizzes."""
    quiz_files = list(ROOT.rglob("quizzes/*.yaml")) + list(ROOT.rglob("quizzes/*.yml"))
    yaml_slugs: set[str] = set()

    with Session(engine) as session:
        for file in quiz_files:
            if ".github" in file.parts:
                continue

            # Derive category from path: ROOT/{category}/quizzes/{slug}.yaml
            rel = file.relative_to(ROOT)
            parts = rel.parts  # e.g., ("docker", "quizzes", "docker-layers.yaml")
            if len(parts) < 3 or parts[-2] != "quizzes":
                continue
            category = parts[0].replace(" ", "-")
            slug = file.stem  # filename without extension

            try:
                data = yaml.safe_load(file.read_text()) or {}
            except Exception as e:
                logger.warning("Skipping %s: YAML parse error: %s", file, e)
                continue

            if not isinstance(data, dict):
                logger.warning("Skipping %s: root is %s, not dict", file, type(data).__name__)
                continue

            title = data.get("title", slug.replace("-", " ").title())
            lesson_slug = data.get("lesson_slug")
            raw_questions = data.get("questions", [])

            if not isinstance(raw_questions, list):
                logger.warning("Skipping %s: questions is not a list", file)
                continue

            quiz = Quiz(
                title=title,
                slug=slug,
                category=category,
                lesson_slug=lesson_slug,
            )
            upsert_quiz(quiz, raw_questions, session)
            yaml_slugs.add(slug)

        # Remove orphan quizzes no longer in files
        all_db_quizzes = session.exec(select(Quiz)).all()
        orphans = [q for q in all_db_quizzes if q.slug not in yaml_slugs]
        if len(orphans) > len(all_db_quizzes) * 0.5:
            logger.warning(
                "Skipping orphan removal: %d of %d quizzes would be deleted (>50%%)",
                len(orphans),
                len(all_db_quizzes),
            )
        else:
            for quiz in orphans:
                logger.info("Removing orphaned quiz: %s", quiz.slug)
                session.delete(quiz)

        session.commit()
