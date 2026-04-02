import calendar
from datetime import date

def end_of_month(d: date) -> date:
    last_day = calendar.monthrange(d.year, d.month)[1]
    return d.replace(day=last_day)

def is_end_of_month(d: date) -> bool:
    return d == end_of_month(d)

def next_15_or_eom(d: date) -> date:
    """Given a date that is either 15 or EOM, return the next payment date alternating."""
    if d.day == 15:
        return end_of_month(d)
    if is_end_of_month(d):
        # move to next month day 15
        if d.month == 12:
            return date(d.year + 1, 1, 15)
        return date(d.year, d.month + 1, 15)
    # If not 15/EOM, normalize: if <=15 -> 15, else -> EOM
    if d.day <= 15:
        return d.replace(day=15)
    else:
        return end_of_month(d)
