from sqlalchemy import text

from app import create_app
from app.extensions import db

app = create_app()

with app.app_context():
    try:
        with db.engine.connect() as conn:
            version = conn.execute(text("SELECT @@VERSION")).scalar()
            db_name = conn.execute(text("SELECT DB_NAME()")).scalar()
            print("Connection OK")
            print("Database:", db_name)
            print("Server  :", version.splitlines()[0])
    except Exception as exc:
        print("Connection FAILED")
        print(exc)
