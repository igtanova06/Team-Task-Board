import pytest
from app import create_app


@pytest.fixture
def client():
    app = create_app("testing")
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client


def test_get_board_tasks_skeleton(client):
    response = client.get("/api/boards/1/tasks")
    assert response.status_code == 200
    json_data = response.get_json()
    assert json_data["success"] is True
    assert "tasks" in json_data["data"]


def test_update_status_skeleton(client):
    response = client.put("/api/tasks/1/status", json={"status": "in_progress"})
    assert response.status_code == 200
    json_data = response.get_json()
    assert json_data["success"] is True
    assert json_data["data"]["status"] == "in_progress"

    # Test invalid status
    invalid_res = client.put("/api/tasks/1/status", json={"status": "invalid_status"})
    assert invalid_res.status_code == 400


def test_add_comment_skeleton(client):
    response = client.post("/api/tasks/1/comments", json={"content": "Great task!"})
    assert response.status_code == 200
    json_data = response.get_json()
    assert json_data["success"] is True
    assert json_data["data"]["content"] == "Great task!"

    # Test empty comment
    empty_res = client.post("/api/tasks/1/comments", json={"content": "   "})
    assert empty_res.status_code == 400
