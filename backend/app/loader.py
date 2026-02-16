from pathlib import Path

import yaml
from sqlmodel import Session, select

from .database import engine
from .models import Flashcard

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
    """
    yaml_paths = list(ROOT.rglob("*.yml")) + list(ROOT.rglob("*.yaml"))

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
                print(f"Skipping {file}: root is {type(data).__name__}, not list")
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
        session.commit()
