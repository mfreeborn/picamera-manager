import datetime
import re


def validate_filename(filename: str) -> str:
    """Validate the filename and return an error message if invalid."""
    error_text = ""
    if not filename or len(filename) > 100:
        error_text = "Filenames must be between 1 and 100 characters long"
    else:
        pattern = r"^[\w :-]+$"
        if re.fullmatch(pattern, filename) is None:
            error_text = "Filenames may only contain alphanumeric characters, spaces, _, - or :'"
    return error_text


def validate_date_range(start_date: datetime.datetime, end_date: datetime.datetime) -> str:
    """Validate the selected date range and return an error message if invalid."""
    if end_date <= start_date:
        return "'End' must be later than 'Start'"
    return ""


def validate_fps(fps: int) -> str:
    """Validate the frames per second and return an error message if invalid."""
    error_text = ""
    if not isinstance(fps, int) or not fps or fps > 120:
        error_text = "FPS must be an integer between 1 and 120"
    return error_text


def validate_divisor(divisor: int, fps: int):
    """Validate the divisor and return an error message if invalid."""
    error_text = ""
    if not isinstance(divisor, int) or divisor < 1:
        error_text = "Divisor must be an integer greater than 1"
    return error_text
