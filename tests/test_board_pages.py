"""Board list / settings / members pages (HTML shells). The behaviour is covered by the API tests
(test_board_api.py) and the browser e2e run; here we check routing, permissions and the hooks the JS needs."""
from tests.conftest import login


def test_home_redirects_to_board_list(app, world):
    r = login(app, "alex").get("/")
    assert r.status_code == 302 and r.headers["Location"].endswith("/boards")


def test_board_list_requires_login(app, world):
    r = app.test_client().get("/boards")
    assert r.status_code == 302 and "/login" in r.headers["Location"]


def test_board_list_page_has_ajax_hooks(app, world):
    html = login(app, "eve").get("/boards").get_data(as_text=True)      # eve owns one board
    for hook in ('id="boardGrid"', 'id="btnNewBoard"', 'id="boardModal"', 'id="boardSwitcherMenu"',
                 'data-user-id=', 'name="csrf-token"', "kanban/js/boards.js"):
        assert hook in html


def test_owner_sees_settings_button_viewer_does_not(app, world):
    owner = login(app, "alex").get(f"/boards/{world['board']}").get_data(as_text=True)
    viewer = login(app, "dave").get(f"/boards/{world['board']}").get_data(as_text=True)
    assert 'id="btnBoardSettings"' in owner and 'id="btnMembers"' in owner
    assert 'id="btnBoardSettings"' not in viewer and 'id="btnMembers"' in viewer     # everyone can see members


def test_members_payload_has_emails_for_the_dialog(app, world):
    body = login(app, "dave").get(f"/api/boards/{world['board']}").get_json()
    assert all(m["email"].endswith("@example.com") for m in body["members"])
    assert {m["role"] for m in body["members"]} == {"owner", "member", "viewer"}


def test_outsider_cannot_open_board_page_or_members(app, world):
    c = login(app, "eve")
    assert c.get(f"/boards/{world['board']}").status_code == 404
    assert c.get(f"/api/boards/{world['board']}").status_code == 404
