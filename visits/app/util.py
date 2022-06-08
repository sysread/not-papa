from calendar import monthrange
from datetime import datetime, timezone


UTC = timezone.utc


def utcnow():
    """Returns a UTC datetime object for the current time and date.
    """
    return datetime.now(UTC)


def first_day_of_month(month, year):
    """Returns a datetime object representing the first day of the month/year
    supplied. TZ is UTC.
    """
    return datetime(year, month, monthrange(year, month)[0], tzinfo=UTC)


def last_day_of_month(month, year):
    """Returns a datetime object representing the last day of the month/year
    supplied. TZ is UTC.
    """
    return datetime(year, month, monthrange(year, month)[1], tzinfo=UTC)
