import logging
import re
from datetime import datetime, timezone
from pathlib import Path

import yaml
from sqlmodel import Session, select

from .database import engine
from .models import Flashcard, Lesson

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
        for lesson in all_db_lessons:
            if lesson.slug not in yaml_slugs:
                logger.info("Removing orphaned lesson: %s", lesson.slug)
                session.delete(lesson)

        session.commit()
