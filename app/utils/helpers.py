# app/utils/helpers.py
# General helper functions.

import datetime

def format_month_name(month_number):
    """Converts a month number (1-12) to its full name."""
    if not month_number:
        return ""
    try:
        month_num = int(month_number)
        if 1 <= month_num <= 12:
            # Create a date object for the first day of that month in a non-leap year
            return datetime.date(1900, month_num, 1).strftime('%B')
    except ValueError:
        pass # If month_number is not a valid integer
    return str(month_number) # Fallback to returning the number as string if invalid
