import pytest
from app.extensions import db
from app.models import User, Board, BoardMembership, Role


def test_register_page_loads(app):
    client = app.test_client()
    res = client.get('/register')
    assert res.status_code == 200
    assert b'Create an account' in res.data
    assert b'username' in res.data
    assert b'email' in res.data
    assert b'password' in res.data


def test_register_creates_user_in_db(app):
    client = app.test_client()
    with app.app_context():
        res = client.post('/register', data={
            'username': 'member2_user',
            'email': 'member2@example.com',
            'password': 'Password123',
            'confirm_password': 'Password123'
        }, follow_redirects=True)
        assert res.status_code == 200

        user = User.query.filter_by(username='member2_user').first()
        assert user is not None
        assert user.email == 'member2@example.com'
        assert user.password_hash != 'Password123'
        assert user.check_password('Password123') is True
        assert user.check_password('WrongPassword') is False


def test_register_duplicate_rejected(app):
    client = app.test_client()
    with app.app_context():
        u = User(username='existing_user', email='existing@example.com')
        u.set_password('Password123')
        db.session.add(u)
        db.session.commit()

        # Duplicate username
        res_dup_name = client.post('/register', data={
            'username': 'existing_user',
            'email': 'new_unique@example.com',
            'password': 'Password123',
            'confirm_password': 'Password123'
        })
        assert res_dup_name.status_code == 422

        # Duplicate email
        res_dup_email = client.post('/register', data={
            'username': 'new_unique_name',
            'email': 'existing@example.com',
            'password': 'Password123',
            'confirm_password': 'Password123'
        })
        assert res_dup_email.status_code == 422


def test_jwt_api_login_and_bearer_auth(app):
    client = app.test_client()
    with app.app_context():
        u = User(username='jwt_user', email='jwt@example.com')
        u.set_password('Password123')
        board = Board(name='JWT Test Board')
        db.session.add_all([u, board])
        db.session.flush()

        mem = BoardMembership(user_id=u.id, board_id=board.id, role=Role.OWNER)
        db.session.add(mem)
        db.session.commit()

        # 1. API Login returns JWT
        res_login = client.post('/auth/login', json={
            'identity': 'jwt_user',
            'password': 'Password123'
        })
        assert res_login.status_code == 200
        token = res_login.get_json()['access_token']
        assert token is not None

        # 2. Wrong password returns 401
        res_bad = client.post('/auth/login', json={
            'identity': 'jwt_user',
            'password': 'WrongPassword'
        })
        assert res_bad.status_code == 401

        # 3. Call protected API with Bearer token
        res_api = client.get(f'/api/boards/{board.id}/tasks', headers={
            'Authorization': f'Bearer {token}'
        })
        assert res_api.status_code == 200
        assert isinstance(res_api.get_json(), list)
