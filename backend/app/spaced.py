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
