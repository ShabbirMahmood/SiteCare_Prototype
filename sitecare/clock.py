"""Request-scoped application time; authentication always uses the real clock."""
from contextvars import ContextVar
from datetime import datetime, timedelta, timezone


clock_offset = ContextVar("sitecare_clock_offset", default=0.0)


def system_now():
    return datetime.now(timezone.utc)


def now_utc():
    return system_now() + timedelta(seconds=clock_offset.get())


def read_clock(db):
    return dict(db.execute("SELECT * FROM app_clock WHERE id=1").fetchone())


def describe_clock(config):
    actual = system_now()
    effective = actual + timedelta(seconds=config["offset_seconds"] or 0)
    return {"mode": "system" if config["offset_seconds"] is None else "manual",
            "now": effective.isoformat(), "system_now": actual.isoformat(),
            "selected_at": config["selected_at"], "revision": config["revision"]}
