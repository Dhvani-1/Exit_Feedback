import pytest
from datetime import date
from app.services.date_calculator import calculate_feedback_due_date


def test_standard_dates():
    assert calculate_feedback_due_date(date(2026, 1, 15)) == date(2026, 4, 15)
    assert calculate_feedback_due_date(date(2026, 2, 10)) == date(2026, 5, 10)
    assert calculate_feedback_due_date(date(2026, 3, 5)) == date(2026, 6, 5)


def test_month_end_clamping_31st_day():
    # 31 Jan -> 30 Apr (April has 30 days)
    assert calculate_feedback_due_date(date(2026, 1, 31)) == date(2026, 4, 30)
    # 31 May -> 31 Aug (August has 31 days)
    assert calculate_feedback_due_date(date(2026, 5, 31)) == date(2026, 8, 31)
    # 31 Aug -> 30 Nov (November has 30 days)
    assert calculate_feedback_due_date(date(2026, 8, 31)) == date(2026, 11, 30)


def test_november_to_february_non_leap_year():
    # 30 Nov 2026 -> 28 Feb 2027
    assert calculate_feedback_due_date(date(2026, 11, 30)) == date(2027, 2, 28)


def test_november_to_february_leap_year():
    # 30 Nov 2027 -> 29 Feb 2028
    assert calculate_feedback_due_date(date(2027, 11, 30)) == date(2028, 2, 29)


def test_leap_year_january_31():
    # 31 Jan 2028 -> 30 Apr 2028
    assert calculate_feedback_due_date(date(2028, 1, 31)) == date(2028, 4, 30)


def test_leap_year_february_29():
    # 29 Feb 2028 -> 29 May 2028
    assert calculate_feedback_due_date(date(2028, 2, 29)) == date(2028, 5, 29)


def test_year_rollover():
    # 15 Oct 2026 -> 15 Jan 2027
    assert calculate_feedback_due_date(date(2026, 10, 15)) == date(2027, 1, 15)
    # 31 Dec 2026 -> 31 Mar 2027
    assert calculate_feedback_due_date(date(2026, 12, 31)) == date(2027, 3, 31)


def test_invalid_input_type():
    with pytest.raises(ValueError):
        calculate_feedback_due_date("2026-01-15")
