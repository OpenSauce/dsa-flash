import logging
from pathlib import Path

import yaml
from sqlmodel import Session, select

from .database import engine
from .models import Flashcard

logger = logging.getLogger(__name__)

ROOT = Path("/data/flashcards")  # mounted via compose


def _dir_metadata(path: Path) -> tuple[str | None, str | None]:
    """
    Derive (category, language) from .../category/(language/)?file.yaml
    """
    parts = path.relative_to(ROOT).parts
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
                    tags=raw.get("tags"),
                    category=category,
                    language=language,
                )
                upsert_flashcard(card, session)
                yaml_keys.add((raw["title"], category, language))

        # Remove cards from DB that are no longer in YAML
        all_db_cards = session.exec(select(Flashcard)).all()
        for db_card in all_db_cards:
            if (db_card.title, db_card.category, db_card.language) not in yaml_keys:
                logger.info("Removing orphaned card: %s (%s/%s)", db_card.title, db_card.category, db_card.language)
                session.delete(db_card)

        session.commit()
