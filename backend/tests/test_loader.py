import logging
from pathlib import Path
from unittest.mock import patch

import yaml
from sqlmodel import Session, select

from app.loader import (
    _dir_metadata,
    _estimate_reading_time,
    _parse_front_matter,
    load_lessons,
    load_yaml_flashcards,
    upsert_flashcard,
)
from app.models import Flashcard, Lesson

# ---------------------------------------------------------------------------
# _dir_metadata
# ---------------------------------------------------------------------------


def test_dir_metadata_1_part(tmp_path):
    """file.yaml directly under ROOT -> (None, None) -- no category directory"""
    file = tmp_path / "file.yaml"
    file.touch()

    with patch("app.loader.ROOT", tmp_path):
        category, language = _dir_metadata(file)

    assert category is None
    assert language is None


def test_dir_metadata_2_parts(tmp_path):
    """category/file.yaml -> (category, None) -- flat category, no language"""
    file = tmp_path / "aws" / "compute.yaml"
    file.parent.mkdir(parents=True)
    file.touch()

    with patch("app.loader.ROOT", tmp_path):
        category, language = _dir_metadata(file)

    assert category == "aws"
    assert language is None


def test_dir_metadata_3_parts(tmp_path):
    """category/language/file.yaml -> (category, language)"""
    file = tmp_path / "data-structures" / "go" / "array.yaml"
    file.parent.mkdir(parents=True)
    file.touch()

    with patch("app.loader.ROOT", tmp_path):
        category, language = _dir_metadata(file)

    assert category == "data-structures"
    assert language == "go"


# ---------------------------------------------------------------------------
# upsert_flashcard
# ---------------------------------------------------------------------------


def _make_card(**kwargs) -> Flashcard:
    defaults = dict(
        title="Test Card",
        front="What is X?",
        back="X is Y.",
        category="test-cat",
        language="go",
        tags=[],
    )
    defaults.update(kwargs)
    return Flashcard(**defaults)


def test_upsert_flashcard_insert(session):
    """A card not in DB is inserted."""
    card = _make_card(title="New Card")
    upsert_flashcard(card, session)
    session.commit()

    results = session.exec(select(Flashcard).where(Flashcard.title == "New Card")).all()
    assert len(results) == 1
    assert results[0].front == "What is X?"


def test_upsert_flashcard_update(session):
    """A card already in DB is updated in-place (no duplicate created)."""
    original = _make_card(title="Existing Card", front="Original front", back="Original back")
    session.add(original)
    session.commit()

    updated = _make_card(title="Existing Card", front="Updated front", back="Updated back")
    upsert_flashcard(updated, session)
    session.commit()

    results = session.exec(select(Flashcard).where(Flashcard.title == "Existing Card")).all()
    assert len(results) == 1
    assert results[0].front == "Updated front"
    assert results[0].back == "Updated back"


# ---------------------------------------------------------------------------
# Helpers for load_yaml_flashcards integration tests
# ---------------------------------------------------------------------------


def _write_yaml(path: Path, cards: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.dump(cards))


def _seed_db(session, cards: list[dict], category: str, language: str | None) -> None:
    for c in cards:
        card = Flashcard(
            title=c["title"],
            front=c["Front"],
            back=c["Back"],
            category=category,
            language=language,
            tags=[],
        )
        session.add(card)
    session.commit()


# ---------------------------------------------------------------------------
# Orphan removal: normal case
# ---------------------------------------------------------------------------


def test_orphan_removal_normal(tmp_path, engine):
    """Cards removed from YAML are deleted when orphan count <= 50%."""
    all_card_data = [
        {"title": f"Card {i}", "Front": f"Q{i}", "Back": f"A{i}"} for i in range(4)
    ]
    with Session(engine) as session:
        _seed_db(session, all_card_data, "cat", "go")

    # YAML contains only 3 of the 4 cards (1 orphan = 25% -> below threshold)
    yaml_card_data = all_card_data[:3]
    _write_yaml(tmp_path / "cat" / "go" / "cards.yaml", yaml_card_data)

    with patch("app.loader.ROOT", tmp_path), patch("app.loader.engine", engine):
        load_yaml_flashcards()

    with Session(engine) as session:
        remaining = session.exec(select(Flashcard)).all()

    assert len(remaining) == 3
    titles = {c.title for c in remaining}
    assert "Card 3" not in titles


# ---------------------------------------------------------------------------
# Orphan removal: safety threshold case
# ---------------------------------------------------------------------------


def test_orphan_removal_boundary_50_percent(tmp_path, engine):
    """Cards are still removed when exactly 50% of cards are orphans."""
    all_card_data = [
        {"title": f"Card {i}", "Front": f"Q{i}", "Back": f"A{i}"} for i in range(4)
    ]
    with Session(engine) as session:
        _seed_db(session, all_card_data, "cat", "go")

    # YAML contains exactly 2 of the 4 cards (2 orphans = 50% -> at threshold, not above)
    yaml_card_data = all_card_data[:2]
    _write_yaml(tmp_path / "cat" / "go" / "cards.yaml", yaml_card_data)

    with patch("app.loader.ROOT", tmp_path), patch("app.loader.engine", engine):
        load_yaml_flashcards()

    with Session(engine) as session:
        remaining = session.exec(select(Flashcard)).all()

    assert len(remaining) == 2
    titles = {c.title for c in remaining}
    assert titles == {c["title"] for c in yaml_card_data}


def test_orphan_removal_safety_threshold(tmp_path, engine, caplog):
    """Orphan removal aborts when orphan count > 50% of total cards."""
    all_card_data = [
        {"title": f"Card {i}", "Front": f"Q{i}", "Back": f"A{i}"} for i in range(4)
    ]
    with Session(engine) as session:
        _seed_db(session, all_card_data, "cat", "go")

    # YAML contains only 1 of 4 cards (3 orphans = 75% -> above threshold)
    yaml_card_data = all_card_data[:1]
    _write_yaml(tmp_path / "cat" / "go" / "cards.yaml", yaml_card_data)

    with caplog.at_level(logging.WARNING, logger="app.loader"):
        with patch("app.loader.ROOT", tmp_path), patch("app.loader.engine", engine):
            load_yaml_flashcards()

    with Session(engine) as session:
        remaining = session.exec(select(Flashcard)).all()

    # All 4 cards preserved -- deletion was aborted
    assert len(remaining) == 4
    assert "Orphan removal aborted" in caplog.text


# ---------------------------------------------------------------------------
# _parse_front_matter
# ---------------------------------------------------------------------------


def test_parse_front_matter_with_valid_front_matter():
    text = "---\ntitle: My Lesson\norder: 1\n---\n# Body\n\nContent here."
    fm, body = _parse_front_matter(text)
    assert fm == {"title": "My Lesson", "order": 1}
    assert "# Body" in body


def test_parse_front_matter_no_front_matter():
    text = "# Just a heading\n\nContent."
    fm, body = _parse_front_matter(text)
    assert fm == {}
    assert body == text


def test_parse_front_matter_empty_front_matter():
    text = "---\n\n---\n# Body"
    fm, body = _parse_front_matter(text)
    assert fm == {}
    assert "# Body" in body


# ---------------------------------------------------------------------------
# _estimate_reading_time
# ---------------------------------------------------------------------------


def test_estimate_reading_time_short_text():
    # Under 200 words -> minimum 1 minute
    text = "hello world"
    assert _estimate_reading_time(text) == 1


def test_estimate_reading_time_400_words():
    text = " ".join(["word"] * 400)
    assert _estimate_reading_time(text) == 2


def test_estimate_reading_time_rounding():
    # 250 words -> round(250/200) = round(1.25) = 1 (banker's rounding)
    text = " ".join(["word"] * 250)
    result = _estimate_reading_time(text)
    assert result >= 1


# ---------------------------------------------------------------------------
# load_lessons integration tests
# ---------------------------------------------------------------------------


def _write_lesson(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)


def test_load_lessons_basic(tmp_path, engine):
    """Lesson file is loaded into the DB with correct fields."""
    content = (
        "---\ntitle: Docker Basics\norder: 1\n"
        "summary: Learn Docker fundamentals.\n---\n"
        "# Docker\n\nContainers are lightweight.\n"
    )
    _write_lesson(tmp_path / "docker" / "lessons" / "docker-basics.md", content)

    with patch("app.loader.ROOT", tmp_path), patch("app.loader.engine", engine):
        load_lessons()

    with Session(engine) as session:
        lessons = session.exec(select(Lesson)).all()

    assert len(lessons) == 1
    lesson = lessons[0]
    assert lesson.slug == "docker-basics"
    assert lesson.title == "Docker Basics"
    assert lesson.category == "docker"
    assert lesson.order == 1
    assert lesson.summary == "Learn Docker fundamentals."
    assert "Containers are lightweight" in lesson.content
    assert lesson.reading_time_minutes >= 1


def test_load_lessons_upsert(tmp_path, engine):
    """Reloading a modified lesson updates it in-place."""
    content_v1 = "---\ntitle: First Version\norder: 1\nsummary: Summary v1.\n---\n# First\n\nOriginal content.\n"
    lesson_path = tmp_path / "docker" / "lessons" / "upsert-test.md"
    _write_lesson(lesson_path, content_v1)

    with patch("app.loader.ROOT", tmp_path), patch("app.loader.engine", engine):
        load_lessons()

    with Session(engine) as session:
        lessons = session.exec(select(Lesson).where(Lesson.slug == "upsert-test")).all()
    assert len(lessons) == 1
    assert lessons[0].title == "First Version"

    # Update the file
    content_v2 = "---\ntitle: Second Version\norder: 1\nsummary: Summary v2.\n---\n# Second\n\nUpdated content.\n"
    lesson_path.write_text(content_v2)

    with patch("app.loader.ROOT", tmp_path), patch("app.loader.engine", engine):
        load_lessons()

    with Session(engine) as session:
        lessons = session.exec(select(Lesson).where(Lesson.slug == "upsert-test")).all()
    assert len(lessons) == 1
    assert lessons[0].title == "Second Version"
    assert "Updated content" in lessons[0].content


def test_load_lessons_orphan_removal(tmp_path, engine):
    """Lessons removed from files are deleted from DB on reload."""
    content = "---\ntitle: Lesson A\norder: 1\nsummary: A.\n---\n# A\n\nContent A.\n"
    file_a = tmp_path / "docker" / "lessons" / "lesson-a.md"
    file_b = tmp_path / "docker" / "lessons" / "lesson-b.md"
    _write_lesson(file_a, content.replace("Lesson A", "Lesson A").replace("# A", "# A"))
    _write_lesson(file_b, content.replace("Lesson A", "Lesson B").replace("# A", "# B"))

    with patch("app.loader.ROOT", tmp_path), patch("app.loader.engine", engine):
        load_lessons()

    with Session(engine) as session:
        count = len(session.exec(select(Lesson)).all())
    assert count == 2

    # Remove lesson-b
    file_b.unlink()

    with patch("app.loader.ROOT", tmp_path), patch("app.loader.engine", engine):
        load_lessons()

    with Session(engine) as session:
        lessons = session.exec(select(Lesson)).all()
    assert len(lessons) == 1
    assert lessons[0].slug == "lesson-a"


def test_load_lessons_space_in_category_dir(tmp_path, engine):
    """Category directory with spaces is normalized to hyphens."""
    content = "---\ntitle: BST Intro\norder: 1\nsummary: Trees.\n---\n# Trees\n\nBinary search trees.\n"
    _write_lesson(tmp_path / "data structures" / "lessons" / "bst-intro.md", content)

    with patch("app.loader.ROOT", tmp_path), patch("app.loader.engine", engine):
        load_lessons()

    with Session(engine) as session:
        lesson = session.exec(select(Lesson).where(Lesson.slug == "bst-intro")).first()

    assert lesson is not None
    assert lesson.category == "data-structures"


# ---------------------------------------------------------------------------
# lesson_slug field in flashcard loader
# ---------------------------------------------------------------------------


def test_load_flashcards_with_lesson_field(tmp_path, engine):
    """Flashcard YAML with `lesson` field stores it as lesson_slug."""
    cards = [
        {"title": "Card 1", "Front": "Q1", "Back": "A1", "lesson": "docker-layers-build-cache"},
        {"title": "Card 2", "Front": "Q2", "Back": "A2"},
    ]
    _write_yaml(tmp_path / "docker" / "cards.yaml", cards)

    with patch("app.loader.ROOT", tmp_path), patch("app.loader.engine", engine):
        load_yaml_flashcards()

    with Session(engine) as session:
        all_cards = session.exec(select(Flashcard)).all()

    assert len(all_cards) == 2
    by_title = {c.title: c for c in all_cards}
    assert by_title["Card 1"].lesson_slug == "docker-layers-build-cache"
    assert by_title["Card 2"].lesson_slug is None


def test_upsert_flashcard_updates_lesson_slug(session):
    """Upserting a card updates lesson_slug on the existing row."""
    original = _make_card(title="Card", lesson_slug=None)
    session.add(original)
    session.commit()

    updated = _make_card(title="Card", lesson_slug="new-lesson")
    upsert_flashcard(updated, session)
    session.commit()

    results = session.exec(select(Flashcard).where(Flashcard.title == "Card")).all()
    assert len(results) == 1
    assert results[0].lesson_slug == "new-lesson"
