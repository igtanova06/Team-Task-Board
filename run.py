import os
import sys

from app import create_app

app = create_app()

if __name__ == "__main__":
    # The debug reloader starts this file twice; do the DB checks only in the first process.
    if os.environ.get("WERKZEUG_RUN_MAIN") != "true":
        from app.main.demo import ensure_demo_ready
        ensure_demo_ready(app, reseed="--reseed" in sys.argv, assume_yes="--yes" in sys.argv)
    app.run(debug=True)
