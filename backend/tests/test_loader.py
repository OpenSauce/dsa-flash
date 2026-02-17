import logging
from pathlib import Path
from unittest.mock import patch

import yaml
from sqlmodel import Session, select

from app.loader import _dir_metadata, load_yaml_flashcards, upsert_flashcard
from app.models import Flashcard

# ---------------------------------------------------------------------------
# _dir_metadata
# ---------------------------------------------------------------------------


def test_dir_metadata_1_part(tmp_path):
    """file.yaml directly under ROOT -> (filename_as_category, None)"""
    file = tmp_path / "file.yaml"
    file.touch()

    with patch("app.loader.ROOT", tmp_path):
        category, language = _dir_metadata(file)

    assert category == "file.yaml"
    assert language is None


def test_dir_metadata_2_parts(tmp_path):
    """category/file.yaml -> (category, file.yaml)"""
    file = tmp_path / "aws" / "compute.yaml"
    file.parent.mkdir(parents=True)
    file.touch()

    with patch("app.loader.ROOT", tmp_path):
        category, language = _dir_metadata(file)

    assert category == "aws"
    assert language == "compute.yaml"


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
