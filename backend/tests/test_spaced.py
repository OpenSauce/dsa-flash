import pytest

from app.models import UserFlashcard
from app.spaced import sm2


def make_card(**kwargs) -> UserFlashcard:
    defaults = {
        "repetitions": 0,
        "interval": 1,
        "easiness": 2.5,
    }
    defaults.update(kwargs)
    return UserFlashcard(**defaults)


def test_quality_0_resets_repetitions_and_interval():
    card = make_card(repetitions=3, interval=10, easiness=2.5)
    sm2(card, quality=0)
    assert card.repetitions == 0
    assert card.interval == 1


def test_quality_0_reduces_easiness():
    card = make_card(easiness=2.5)
    sm2(card, quality=0)
    assert card.easiness < 2.5


def test_quality_5_increases_easiness():
    card = make_card(easiness=2.5)
    sm2(card, quality=5)
    assert card.easiness > 2.5


def test_easiness_floor_never_below_1_3():
    card = make_card(easiness=1.3)
    sm2(card, quality=0)
    assert card.easiness >= 1.3


def test_easiness_floor_after_repeated_low_quality():
    card = make_card(easiness=1.4)
    for _ in range(5):
        sm2(card, quality=0)
    assert card.easiness >= 1.3


def test_quality_3_first_rep_sets_interval_to_1():
    card = make_card(repetitions=0, interval=1, easiness=2.5)
    sm2(card, quality=3)
    assert card.repetitions == 1
    assert card.interval == 1


def test_quality_3_second_rep_sets_interval_to_6():
    card = make_card(repetitions=1, interval=1, easiness=2.5)
    sm2(card, quality=3)
    assert card.repetitions == 2
    assert card.interval == 6


def test_quality_3_third_rep_multiplies_interval_by_easiness():
    card = make_card(repetitions=2, interval=6, easiness=2.5)
    sm2(card, quality=3)
    assert card.repetitions == 3
    # SM-2 updates easiness first, then uses new easiness for interval multiplication
    expected_ef = max(1.3, 2.5 + (0.1 - (5 - 3) * (0.08 + (5 - 3) * 0.02)))
    assert card.interval == int(round(6 * expected_ef))


def test_interval_multiplication_uses_updated_easiness():
    card = make_card(repetitions=2, interval=6, easiness=2.0)
    sm2(card, quality=5)
    expected_ef = 2.0 + (0.1 - (5 - 5) * (0.08 + (5 - 5) * 0.02))
    expected_interval = round(6 * expected_ef)
    assert card.interval == expected_interval


def test_quality_below_3_resets_regardless_of_repetitions():
    card = make_card(repetitions=5, interval=30, easiness=2.5)
    sm2(card, quality=2)
    assert card.repetitions == 0
    assert card.interval == 1


def test_invalid_quality_raises_value_error():
    card = make_card()
    with pytest.raises(ValueError):
        sm2(card, quality=6)
    with pytest.raises(ValueError):
        sm2(card, quality=-1)


def test_next_review_is_set_after_review():
    card = make_card()
    assert card.next_review is None
    sm2(card, quality=3)
    assert card.next_review is not None


def test_last_reviewed_is_set_after_review():
    card = make_card()
    assert card.last_reviewed is None
    sm2(card, quality=3)
    assert card.last_reviewed is not None
