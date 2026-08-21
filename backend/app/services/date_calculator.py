import calendar
from datetime import date, datetime, time, timedelta
import pytz


def calculate_feedback_due_date(last_working_date: date) -> date:
    """
    Calculates the feedback due date as exactly 3 calendar months after the last working date.
    
    Rules:
    - Target month is 3 calendar months ahead.
    - If target month has fewer days than the original day of month, clamp to the last valid day of target month.
    - Pure calendar arithmetic (timezone-independent).
    """
    if not isinstance(last_working_date, date):
        raise ValueError("last_working_date must be a valid datetime.date object")

    year = last_working_date.year
    month = last_working_date.month
    day = last_working_date.day

    target_month_raw = month + 3
    target_year = year + (target_month_raw - 1) // 12
    target_month = (target_month_raw - 1) % 12 + 1

    max_days = calendar.monthrange(target_year, target_month)[1]
    target_day = min(day, max_days)

    return date(target_year, target_month, target_day)


def compute_scheduled_at(
    feedback_due_date: date,
    send_hour: int = 9,
    timezone_str: str = "Asia/Kolkata",
    weekend_behavior: str = "SEND_ON_DUE_DATE",
) -> datetime:
    """
    Converts a Phase 1 calendar due date into a UTC datetime for email scheduling.
    
    Parameters:
    - feedback_due_date: Authoritative calendar date from Phase 1.
    - send_hour: Hour of the day (0-23) in the local timezone.
    - timezone_str: IANA timezone string (e.g., 'Asia/Kolkata', 'UTC').
    - weekend_behavior: 'SEND_ON_DUE_DATE', 'NEXT_WORKING_DAY', or 'PREVIOUS_WORKING_DAY'.
    
    Returns:
    - Naive datetime object representing the scheduled time in UTC.
    """
    target_date = feedback_due_date

    # Apply weekend behavior adjustments without modifying employee.feedback_due_date
    if weekend_behavior == "NEXT_WORKING_DAY":
        # Saturday -> Monday (+2 days), Sunday -> Monday (+1 day)
        if target_date.weekday() == 5:
            target_date += timedelta(days=2)
        elif target_date.weekday() == 6:
            target_date += timedelta(days=1)
    elif weekend_behavior == "PREVIOUS_WORKING_DAY":
        # Saturday -> Friday (-1 day), Sunday -> Friday (-2 days)
        if target_date.weekday() == 5:
            target_date -= timedelta(days=1)
        elif target_date.weekday() == 6:
            target_date -= timedelta(days=2)

    # Combine date with local send hour
    local_dt = datetime.combine(target_date, time(hour=send_hour, minute=0, second=0))

    # Localize to configured application timezone
    tz = pytz.timezone(timezone_str)
    localized_dt = tz.localize(local_dt)

    # Convert to UTC and return as naive UTC datetime suitable for DB storage
    utc_dt = localized_dt.astimezone(pytz.utc)
    return utc_dt.replace(tzinfo=None)
