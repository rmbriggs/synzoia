from datetime import date
from backend.app.services.windows import rolling_bounds, cap_and_sum


def test_rolling_7_day_window_is_inclusive_and_ends_at_anchor():
    assert rolling_bounds(date(2026, 6, 2), 7) == (date(2026, 5, 27), date(2026, 6, 2))


def test_rolling_30_day_window():
    assert rolling_bounds(date(2026, 6, 2), 30) == (date(2026, 5, 4), date(2026, 6, 2))


def test_window_of_one_day_is_just_the_anchor():
    assert rolling_bounds(date(2026, 6, 2), 1) == (date(2026, 6, 2), date(2026, 6, 2))


def test_cap_and_sum_caps_each_day_then_sums_per_user():
    rows = [
        (1, date(2026, 6, 1), 8000),
        (1, date(2026, 6, 2), 30000),   # capped to 20000
        (2, date(2026, 6, 1), 12000),
    ]
    assert cap_and_sum(rows, 20000) == {1: 28000, 2: 12000}


def test_cap_and_sum_empty():
    assert cap_and_sum([], 20000) == {}
