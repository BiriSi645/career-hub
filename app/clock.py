from datetime import datetime
from zoneinfo import ZoneInfo


ISTANBUL = ZoneInfo("Europe/Istanbul")


def local_today():
    return datetime.now(ISTANBUL).date()


def local_time(value):
    return value.astimezone(ISTANBUL)
