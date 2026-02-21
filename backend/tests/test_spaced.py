import pytest

from app.models import UserFlashcard
from app.spaced import compute_projected_intervals, format_interval, sm2, sm2_preview


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


# ── sm2_preview tests ─────────────────────────────────────────────────────


def test_sm2_preview_quality_below_3_returns_1():
    assert sm2_preview(repetitions=3, interval=10, easiness=2.5, quality=1) == 1
    assert sm2_preview(repetitions=3, interval=10, easiness=2.5, quality=2) == 1
    assert sm2_preview(repetitions=3, interval=10, easiness=2.5, quality=0) == 1


def test_sm2_preview_quality_3_first_rep_returns_1():
    assert sm2_preview(repetitions=0, interval=0, easiness=2.5, quality=3) == 1


def test_sm2_preview_quality_3_second_rep_returns_6():
    assert sm2_preview(repetitions=1, interval=1, easiness=2.5, quality=3) == 6


def test_sm2_preview_quality_5_third_rep_multiplies_interval():
    # reps=2, so new_reps=3 -> multiply interval by updated ef
    ef = 2.5 + (0.1 - (5 - 5) * (0.08 + (5 - 5) * 0.02))
    expected = int(round(10 * ef))
    assert sm2_preview(repetitions=2, interval=10, easiness=2.5, quality=5) == expected


def test_sm2_preview_quality_5_high_easiness():
    ef = max(1.3, 3.0 + (0.1 - (5 - 5) * (0.08 + (5 - 5) * 0.02)))
    expected = int(round(6 * ef))
    assert sm2_preview(repetitions=2, interval=6, easiness=3.0, quality=5) == expected


def test_sm2_preview_invalid_quality_raises_value_error():
    with pytest.raises(ValueError):
        sm2_preview(0, 0, 2.5, quality=6)
    with pytest.raises(ValueError):
        sm2_preview(0, 0, 2.5, quality=-1)


def test_sm2_preview_does_not_mutate_inputs():
    repetitions = 2
    interval = 10
    easiness = 2.5
    sm2_preview(repetitions, interval, easiness, quality=5)
    assert repetitions == 2
    assert interval == 10
    assert easiness == 2.5


# ── format_interval tests ─────────────────────────────────────────────────


def test_format_interval_days_less_than_30():
    assert format_interval(1) == "1d"
    assert format_interval(7) == "7d"
    assert format_interval(14) == "14d"
    assert format_interval(29) == "29d"


def test_format_interval_months_30_plus():
    assert format_interval(30) == "1mo"
    assert format_interval(60) == "2mo"
    assert format_interval(90) == "3mo"
    assert format_interval(365) == "12mo"


# ── compute_projected_intervals tests ────────────────────────────────────


def test_compute_projected_intervals_default_state():
    result = compute_projected_intervals()
    assert isinstance(result, dict)
    assert set(result.keys()) == {"1", "3", "5"}
    # New card (reps=0): all qualities return 1d on first review
    assert result["1"] == "1d"
    assert result["3"] == "1d"
    assert result["5"] == "1d"


def test_compute_projected_intervals_with_custom_state():
    # After 2 successful reviews (reps=2, interval=6): quality 5 should give ~15d
    result = compute_projected_intervals(repetitions=2, interval=6, easiness=2.5)
    assert result["1"] == "1d"
    # quality 3: ef = 2.5 + (0.1 - 2*0.08 - 4*0.02) = 2.5 - 0.06 = 2.44
    ef3 = max(1.3, 2.5 + (0.1 - (5 - 3) * (0.08 + (5 - 3) * 0.02)))
    expected_3 = format_interval(int(round(6 * ef3)))
    assert result["3"] == expected_3
    # quality 5: ef = 2.5 + 0.1 = 2.6
    ef5 = max(1.3, 2.5 + (0.1 - (5 - 5) * (0.08 + (5 - 5) * 0.02)))
    expected_5 = format_interval(int(round(6 * ef5)))
    assert result["5"] == expected_5
