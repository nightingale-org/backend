from __future__ import annotations

import datetime


def current_timeaware_utc_datetime() -> datetime.datetime:
    return datetime.datetime.now(datetime.UTC)
