"""`python run.py` must leave any machine with a reachable database that already holds demo data."""
import pytest

from app import create_app
from app.extensions import db
from app.main.demo import ensure_demo_ready, summary
from app.models import User, Task


def _fresh_app(tmp_path):
    import config
    class Cfg(config.TestingConfig):
        SQLALCHEMY_DATABASE_URI = f"sqlite:///{tmp_path / 'demo.db'}"
    config.config_by_name["tmp"] = Cfg
    return create_app("tmp")


def test_empty_database_gets_tables_and_seed(tmp_path):
    app = _fresh_app(tmp_path)
    counts = ensure_demo_ready(app)
    assert counts["users"] == 4 and counts["boards"] == 1 and counts["tasks"] == 8 and counts["memberships"] == 4
    with app.app_context():
        assert User.query.filter_by(username="Alex").first().check_password("Password123")


def test_existing_data_is_never_overwritten(tmp_path):
    app = _fresh_app(tmp_path)
    ensure_demo_ready(app)
    with app.app_context():
        db.session.add(Task(title="Teammate work", board_id=1, created_by=1))
        db.session.commit()
    counts = ensure_demo_ready(app)                      # second run: no re-seed
    assert counts["tasks"] == 9


def test_reseed_restores_demo_data(tmp_path):
    app = _fresh_app(tmp_path)
    ensure_demo_ready(app)
    with app.app_context():
        Task.query.delete(); db.session.commit()
    assert ensure_demo_ready(app, reseed=True, assume_yes=True)["tasks"] == 8


def test_auto_seed_can_be_disabled(tmp_path, monkeypatch):
    monkeypatch.setenv("AUTO_SEED", "0")
    app = _fresh_app(tmp_path)
    assert ensure_demo_ready(app)["users"] == 0


def test_unreachable_database_exits_with_help(tmp_path, capsys):
    import config
    class Bad(config.TestingConfig):
        SQLALCHEMY_DATABASE_URI = "sqlite:////nonexistent_dir/x/y.db"
    config.config_by_name["bad"] = Bad
    app = create_app("bad")
    with pytest.raises(SystemExit) as e:
        ensure_demo_ready(app)
    assert e.value.code == 1
    assert "Cannot connect" in capsys.readouterr().out
