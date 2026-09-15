"""Local maintenance: python manage.py backup | reset-password USERNAME | check."""
from __future__ import annotations
import argparse
import getpass
from pathlib import Path
from sitecare.storage import initialize, transaction, create_backup, audit
from sitecare.security import password_hash
from sitecare.rules import now_utc


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=["backup", "reset-password", "check"])
    parser.add_argument("username", nargs="?")
    parser.add_argument("--data-dir", type=Path, default=Path(__file__).resolve().parent / "data")
    args = parser.parse_args()
    initialize(args.data_dir)
    if args.command == "backup":
        stamp = now_utc().strftime("%Y%m%dT%H%M%SZ")
        path = Path(__file__).resolve().parent / "backups" / f"sitecare-{stamp}.zip"
        create_backup(args.data_dir, path)
        print(f"Backup created: {path}\nUNENCRYPTED sensitive data. Store on an approved encrypted drive.")
    elif args.command == "check":
        with transaction(args.data_dir) as db:
            print("Database integrity:", db.execute("PRAGMA integrity_check").fetchone()[0])
            missing = [r[0] for r in db.execute("SELECT filename FROM photos")
                       if not (args.data_dir / "photos" / r[0]).is_file()]
            print("Missing photographs:", len(missing))
            if missing:
                raise SystemExit(1)
    else:
        if not args.username:
            raise SystemExit("Use: python manage.py reset-password USERNAME")
        password = getpass.getpass("New password (at least 12 characters): ")
        if len(password) < 12 or len(password) > 128:
            raise SystemExit("Password must contain 12 to 128 characters.")
        if password != getpass.getpass("Repeat password: "):
            raise SystemExit("Passwords do not match.")
        with transaction(args.data_dir, True) as db:
            user = db.execute("SELECT id FROM users WHERE username=?", (args.username,)).fetchone()
            if not user:
                raise SystemExit("User not found.")
            db.execute("UPDATE users SET password_hash=? WHERE id=?", (password_hash(password), user[0]))
            db.execute("DELETE FROM sessions WHERE user_id=?", (user[0],))
            audit(db, "local-maintenance", "password.reset", str(user[0]), {})
        print("Password updated. Existing sessions for this user have been revoked.")


if __name__ == "__main__":
    main()
