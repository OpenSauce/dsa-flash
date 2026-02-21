from datetime import datetime, timedelta, timezone

from .models import UserFlashcard


def sm2(review: UserFlashcard, quality: int) -> None:
    """
    Update a UserFlashcard in-place given quality (0-5).
    ── Raises ValueError if quality ∉ 0‥5.
    """
    if quality not in range(6):
        raise ValueError("quality must be 0–5")

    # 1. Easiness factor
    ef = review.easiness + (0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02))
    review.easiness = max(1.3, ef)

    # 2. Repetitions & interval
    if quality < 3:
        review.repetitions = 0
        review.interval = 1
    else:
        review.repetitions += 1
        if review.repetitions == 1:
            review.interval = 1
        elif review.repetitions == 2:
            review.interval = 6
        else:
            review.interval = int(round(review.interval * review.easiness))

    # 3. Schedule next review
    review.next_review = datetime.now(timezone.utc) + timedelta(days=review.interval)
    review.last_reviewed = datetime.now(timezone.utc)


def sm2_preview(repetitions: int, interval: int, easiness: float, quality: int) -> int:
    """Return the projected interval (days) for a hypothetical review at the given quality."""
    if quality not in range(6):
        raise ValueError("quality must be 0–5")

    ef = easiness + (0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02))
    ef = max(1.3, ef)

    if quality < 3:
        return 1
    else:
        new_reps = repetitions + 1
        if new_reps == 1:
            return 1
        elif new_reps == 2:
            return 6
        else:
            return int(round(interval * ef))


def format_interval(days: int) -> str:
    """Format an interval in days to a human-readable short string."""
    if days < 30:
        return f"{days}d"
    elif days < 365:
        months = max(1, round(days / 30))
        return f"{months}mo"
    else:
        months = round(days / 30)
        return f"{months}mo"


def compute_projected_intervals(
    repetitions: int = 0, interval: int = 0, easiness: float = 2.5
) -> dict[str, str]:
    """Return projected intervals for quality 1, 3, and 5."""
    return {
        "1": format_interval(sm2_preview(repetitions, interval, easiness, 1)),
        "3": format_interval(sm2_preview(repetitions, interval, easiness, 3)),
        "5": format_interval(sm2_preview(repetitions, interval, easiness, 5)),
    }
