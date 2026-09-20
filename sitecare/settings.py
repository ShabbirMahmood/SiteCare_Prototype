"""Persisted installation settings exposed through a request-scoped context."""
from contextvars import ContextVar


keep_calibration = ContextVar("sitecare_keep_calibration", default=False)


def read_settings(db):
    row = dict(db.execute("SELECT * FROM app_settings WHERE id=1").fetchone())
    return {"keep_calibration": bool(row["keep_calibration"]), "revision": row["revision"]}
