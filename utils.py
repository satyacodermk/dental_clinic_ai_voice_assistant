# ===============================================
# ||||||| Date and Time utility functions |||||||
# ===============================================

from datetime import datetime, date, time, timedelta, timezone

# Define Indian Standard Time (UTC+5:30)
IST = timezone(timedelta(hours=5, minutes=30))

def get_today_date() -> date:
    """
    Returns today's date in Indian Standard Time (IST).
    """
    try:
        return datetime.now(IST).date()
    except Exception as e:
        print(f"[ERROR] Failed to get today's date: {e}")
        return None


def get_current_datetime() -> datetime:
    """
    Returns the current date and time in Indian Standard Time (IST).
    """
    try:
        return datetime.now(IST)
    except Exception as e:
        print(f"[ERROR] Failed to get current datetime: {e}")
        return None


def get_current_time() -> time:
    """
    Returns the current time in Indian Standard Time (IST).
    """
    try:
        return datetime.now(IST).time()
    except Exception as e:
        print(f"[ERROR] Failed to get current time: {e}")
        return None


# Example usage
if __name__ == "__main__":
    print("Today's Date:", get_today_date())
    print("Current DateTime:", get_current_datetime())
    print("Current Time:", get_current_time())


