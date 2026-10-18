"""Make sure the database is reachable, has its tables and has demo data BEFORE the app starts.

Used by `python run.py`, so any machine (a teammate's, or the examiner's) opens the site with data:

    python run.py            check connection -> create tables if missing -> seed if the DB is empty
    python run.py --reseed   wipe and re-seed (asks for confirmation; add --yes to skip it)
    AUTO_SEED=0              do not auto-seed (only report)

`python seed.py` keeps working on its own exactly as before.
"""
import os
import sys

from sqlalchemy import inspect, text

from app.extensions import db


def _fail_connection(app, exc):
    uri = app.config.get("SQLALCHEMY_DATABASE_URI", "")
    safe = uri.split("@")[-1] if "@" in uri else uri
    print("\n[DB] Cannot connect to the database.")
    print(f"     target : {safe}")
    print(f"     reason : {str(exc).splitlines()[0][:200]}")
    print("\n     Checklist (see HUONG_DAN_TEST_DB.txt):")
    print("       1. SQL Server is running and the database exists:  CREATE DATABASE TeamTaskBoard;")
    print("       2. .env sits next to run.py and DATABASE_URL is on ONE line")
    print("       3. ODBC driver name matches your machine (17 or 18):")
    print('            python -c "import pyodbc; print(pyodbc.drivers())"')
    print("       4. Add &TrustServerCertificate=yes to DATABASE_URL if you see an SSL error")
    print("       5. Test only the connection:  python check_connection.py")
    print("     No SQL Server? Remove DATABASE_URL from .env to use a local SQLite file instead.\n")
    sys.exit(1)


def _create_tables(app):
    from flask_migrate import upgrade
    print("[DB] Tables not found -> running migrations (flask db upgrade) ...")
    upgrade(directory=os.path.join(os.path.dirname(app.root_path), "migrations"))


def _seed():
    # seed.py sits in the project root (next to run.py); it wipes and re-creates the demo data.
    import seed
    seed.seed()


def summary():
    from app.models import User, Board, BoardMembership, Task, Comment
    return {
        "users": User.query.count(), "boards": Board.query.count(),
        "memberships": BoardMembership.query.count(), "tasks": Task.query.count(),
        "comments": Comment.query.count(),
    }


def ensure_demo_ready(app, *, auto_seed=True, reseed=False, assume_yes=False):
    with app.app_context():
        try:
            with db.engine.connect() as conn:
                conn.execute(text("SELECT 1"))
        except Exception as exc:
            _fail_connection(app, exc)

        engine = db.engine
        label = f"{engine.dialect.name}"
        if app.config.get("USING_SQLITE_FALLBACK"):
            label += " (local fallback file instance/dev.db, DATABASE_URL is not set)"
        print(f"[DB] Connected: {label}")

        if not inspect(engine).has_table("users"):
            _create_tables(app)

        counts = summary()
        if reseed:
            if not assume_yes:
                answer = input(f"[DB] --reseed DELETES ALL data in this database ({counts['tasks']} tasks, "
                               f"{counts['users']} users). Type YES to continue: ")
                if answer.strip() != "YES":
                    print("[DB] Cancelled, nothing changed.")
                    sys.exit(1)
            _seed()
        elif counts["users"] == 0:
            if auto_seed and os.environ.get("AUTO_SEED", "1") != "0":
                print("[DB] Database is empty -> running seed.py ...")
                _seed()
            else:
                print("[DB] WARNING: database is empty. Run `python seed.py` or the board will be blank.")

        counts = summary()
        print("[DB] Ready: " + ", ".join(f"{v} {k}" for k, v in counts.items()))
        if counts["users"] and counts["memberships"]:
            print("[DB] Demo login (password Password123):  alex = owner | ben, chris = members | david = viewer")
        return counts
