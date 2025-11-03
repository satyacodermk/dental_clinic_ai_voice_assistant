import traceback
from typing import Optional, Union
from urllib.parse import quote_plus
from datetime import datetime, date, time, timedelta, timezone

# zoneinfo available in Python 3.9+
try:
    from zoneinfo import ZoneInfo
except Exception:
    ZoneInfo = None  # will still work if user treats naive datetimes as UTC


def _try_parse_date(date_in: Union[str, date, datetime]) -> Optional[date]:
    """Try several common date formats and return a date object, or None on failure."""
    if isinstance(date_in, datetime):
        return date_in.date()
    if isinstance(date_in, date):
        return date_in
    if not isinstance(date_in, str):
        return None

    date_str = date_in.strip()
    formats = [
        "%Y-%m-%d", "%Y/%m/%d", "%d-%m-%Y", "%d/%m/%Y",
        "%d %b %Y", "%d %B %Y", "%b %d %Y", "%B %d %Y",
        "%Y%m%d"
    ]
    for fmt in formats:
        try:
            return datetime.strptime(date_str, fmt).date()
        except Exception:
            pass

    # try ISO parse fallback (YYYY-MM-DDTHH:MM:SS or similar)
    try:
        dt = datetime.fromisoformat(date_str)
        return dt.date()
    except Exception:
        pass

    return None


def _try_parse_time(time_in: Union[str, time, datetime]) -> Optional[time]:
    """Try several common time formats and return a time object, or None on failure."""
    if isinstance(time_in, datetime):
        return time_in.timetz() if time_in.tzinfo else time_in.time()
    if isinstance(time_in, time):
        return time_in
    if not isinstance(time_in, str):
        return None

    t = time_in.strip()
    formats = [
        "%H:%M:%S", "%H:%M", "%I:%M %p", "%I %p", "%H%M", "%H%M%S"
    ]
    for fmt in formats:
        try:
            return datetime.strptime(t, fmt).time()
        except Exception:
            pass

    # try to parse simple numeric like "930" -> 09:30
    if t.isdigit():
        if len(t) in (3, 4):
            hh = int(t[:-2])
            mm = int(t[-2:])
            try:
                return time(hour=hh, minute=mm)
            except Exception:
                pass

    return None


def _to_utc_zstring(dt_obj: datetime, tz_name: Optional[str]) -> str:
    """
    Convert a naive or tz-aware datetime to UTC and return string in format:
    YYYYMMDDTHHMMSSZ
    """
    if dt_obj.tzinfo is None:
        # If user provided a timezone name, attach it; otherwise assume UTC
        if tz_name:
            if ZoneInfo is None:
                raise RuntimeError("ZoneInfo not available in this Python environment.")
            tz = ZoneInfo(tz_name)
            dt_obj = dt_obj.replace(tzinfo=tz)
        else:
            dt_obj = dt_obj.replace(tzinfo=timezone.utc)

    # convert to UTC
    dt_utc = dt_obj.astimezone(timezone.utc)
    return dt_utc.strftime("%Y%m%dT%H%M%SZ")


def create_google_calendar_link(
    title: str,
    app_date: Union[str, date, datetime],
    app_time: Optional[Union[str, time, datetime]] = None,
    duration_minutes: int = 30,
    details: Optional[str] = None,
    location: Optional[str] = None,
    timezone: Optional[str] = "Asia/Kolkata",
    all_day: bool = False,
) -> Optional[str]:
    """
    Build a Google Calendar "create event" link.

    Args:
        title: Event title (will be URL-encoded).
        app_date: Event date (str or date/datetime). Common string formats are supported.
        app_time: Event time (str or time/datetime). If None and all_day=False, defaults to 00:00.
        duration_minutes: Event duration in minutes (ignored for all-day events).
        details: Event description/details (optional).
        location: Event location (optional).
        timezone: IANA timezone name like "Asia/Kolkata" or "UTC". If provided, parsed datetimes
                  will be interpreted in this timezone and converted to UTC for the link.
                  If None, naive datetimes are treated as UTC.
        all_day: If True, create an all-day event (dates use YYYYMMDD format; end date is next day).

    Returns:
        A URL string for Google Calendar that will pre-fill the event, or None on error.
    """
    try:
        if not title or not isinstance(title, str):
            print("Error: title must be a non-empty string.")
            return None

        # Parse date
        parsed_date = _try_parse_date(app_date)
        if parsed_date is None:
            print(f"Error: Couldn't parse app_date: {app_date!r}")
            return None

        if all_day:
            # For all-day events Google expects YYYYMMDD/YYYYMMDD (end date is exclusive)
            start_str = parsed_date.strftime("%Y%m%d")
            end_date = parsed_date + timedelta(days=1)
            end_str = end_date.strftime("%Y%m%d")
            dates_param = f"{start_str}/{end_str}"
        else:
            # Parse time (or default to midnight)
            parsed_time = _try_parse_time(app_time) if app_time is not None else None
            if parsed_time is None:
                # default 00:00 if time not provided
                parsed_time = time(0, 0)

            # build a datetime object
            start_dt = datetime.combine(parsed_date, parsed_time)

            # convert to utc Z-string (YYYYMMDDTHHMMSSZ) using provided timezone
            try:
                start_z = _to_utc_zstring(start_dt, timezone)
            except Exception as e:
                print(f"Timezone conversion error: {e}")
                # fallback: treat naive as UTC
                start_dt = start_dt.replace(tzinfo=timezone.utc)
                start_z = start_dt.strftime("%Y%m%dT%H%M%SZ")

            # compute end datetime (duration)
            end_dt = start_dt + timedelta(minutes=duration_minutes)
            # convert end to UTC string
            try:
                end_z = _to_utc_zstring(end_dt, timezone)
            except Exception:
                # fallback if conversion fails
                end_dt = end_dt.replace(tzinfo=timezone.utc)
                end_z = end_dt.strftime("%Y%m%dT%H%M%SZ")

            dates_param = f"{start_z}/{end_z}"

        # Build base URL and parameters (URL-encoded)
        base = "https://calendar.google.com/calendar/render?action=TEMPLATE"
        parts = [
            ("text", title),
            ("dates", dates_param)
        ]
        if details:
            parts.append(("details", details))
        if location:
            parts.append(("location", location))

        # Join params with '&' and ensure encoding with quote_plus
        encoded = "&".join(f"{k}={quote_plus(str(v))}" for k, v in parts)
        url = f"{base}&{encoded}"
        return url

    except Exception as e:
        print("Unexpected error while creating Google Calendar link:")
        traceback.print_exc()
        return None


if __name__ == "__main__":
    # Example run
    link = create_google_calendar_link(
        title="Doctor Appointment - Dr Kumar",
        app_date="2025-11-03",
        app_time="14:30",                 # local time in Asia/Kolkata
        duration_minutes=90,
        details="Follow-up visit for skin consultation",
        location="Fix Derma Clinic, Bangalore",
        timezone="Asia/Kolkata"          # will convert to UTC for the link
    )
    print(link)
