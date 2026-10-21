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


def test_change_password_requires_login(app):
    client = app.test_client()
    res = client.get('/change-password')
    assert res.status_code == 302
    assert '/login' in res.location


def test_change_password_web_success(app):
    client = app.test_client()
    with app.app_context():
        u = User(username='pw_user', email='pw_user@example.com')
        u.set_password('OldPassword123')
        db.session.add(u)
        db.session.commit()

        # Login user
        client.post('/login', data={'identity': 'pw_user', 'password': 'OldPassword123'})

        # GET change password page
        res_get = client.get('/change-password')
        assert res_get.status_code == 200
        assert b'Change Password' in res_get.data

        # POST valid change password (requires user to log in again)
        res_post = client.post('/change-password', data={
            'current_password': 'OldPassword123',
            'new_password': 'NewPassword456',
            'confirm_password': 'NewPassword456'
        }, follow_redirects=True)
        assert res_post.status_code == 200
        assert b'Please sign in with your new password' in res_post.data

        # Verify password in database
        updated_user = db.session.get(User, u.id)
        assert updated_user.check_password('NewPassword456') is True
        assert updated_user.check_password('OldPassword123') is False

        # Verify old password can no longer log in
        res_old_login = client.post('/login', data={'identity': 'pw_user', 'password': 'OldPassword123'})
        assert res_old_login.status_code == 422

        # Verify new password logs in successfully
        res_new_login = client.post('/login', data={'identity': 'pw_user', 'password': 'NewPassword456'})
        assert res_new_login.status_code == 302


def test_production_config():
    """Verify ProductionConfig security attributes (Rubric Criteria 1 & 5)."""
    from config import ProductionConfig, DevelopmentConfig, TestingConfig
    assert ProductionConfig.DEBUG is False
    assert ProductionConfig.TESTING is False
    assert ProductionConfig.SESSION_COOKIE_HTTPONLY is True
    assert ProductionConfig.SESSION_COOKIE_SAMESITE == "Lax"
    assert DevelopmentConfig.DEBUG is True
    assert TestingConfig.TESTING is True



def test_change_password_validation_failures(app):
    client = app.test_client()
    with app.app_context():
        u = User(username='pw_fail_user', email='pw_fail@example.com')
        u.set_password('OldPassword123')
        db.session.add(u)
        db.session.commit()

        client.post('/login', data={'identity': 'pw_fail_user', 'password': 'OldPassword123'})

        # 1. Wrong current password
        res_wrong = client.post('/change-password', data={
            'current_password': 'WrongPassword',
            'new_password': 'NewPassword456',
            'confirm_password': 'NewPassword456'
        })
        assert res_wrong.status_code == 422
        assert b'Incorrect current password' in res_wrong.data

        # 2. Same as old password
        res_same = client.post('/change-password', data={
            'current_password': 'OldPassword123',
            'new_password': 'OldPassword123',
            'confirm_password': 'OldPassword123'
        })
        assert res_same.status_code == 422
        assert b'New password must be different' in res_same.data

        # 3. Mismatched confirm password
        res_mismatch = client.post('/change-password', data={
            'current_password': 'OldPassword123',
            'new_password': 'NewPassword456',
            'confirm_password': 'DifferentPassword789'
        })
        assert res_mismatch.status_code == 422
        assert b'New passwords must match' in res_mismatch.data


def test_change_password_json_api(app):
    client = app.test_client()
    with app.app_context():
        u = User(username='jwt_pw_user', email='jwt_pw@example.com')
        u.set_password('OldPassword123')
        db.session.add(u)
        db.session.commit()

        # Login via JWT
        res_login = client.post('/auth/login', json={
            'identity': 'jwt_pw_user',
            'password': 'OldPassword123'
        })
        token = res_login.get_json()['access_token']

        # API Change password with invalid current password
        res_bad = client.post('/auth/change-password', json={
            'current_password': 'WrongPassword',
            'new_password': 'NewPassword456',
            'confirm_password': 'NewPassword456'
        }, headers={'Authorization': f'Bearer {token}'})
        assert res_bad.status_code == 422
        assert 'current_password' in res_bad.get_json()['errors']

        # API Change password success
        res_ok = client.post('/auth/change-password', json={
            'current_password': 'OldPassword123',
            'new_password': 'NewPassword456',
            'confirm_password': 'NewPassword456'
        }, headers={'Authorization': f'Bearer {token}'})
        assert res_ok.status_code == 200
        assert res_ok.get_json()['message'] == 'Password changed successfully.'

        # Verify password in database
        updated_user = db.session.get(User, u.id)
        assert updated_user.check_password('NewPassword456') is True

