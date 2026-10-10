from flask import request, jsonify
from app.api import api
from app.models.task import TaskStatus


@api.get("/boards/<int:board_id>/tasks")
def get_board_tasks(board_id):
    return jsonify({
        "success": True,
        "data": {
            "tasks": []
        },
        "message": "Mock response - board tasks"
    }), 200


@api.put("/tasks/<int:task_id>/status")
def update_status(task_id):
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify({
            "success": False,
            "error": "JSON object required"
        }), 400

    status = data.get("status")
    if not isinstance(status, str) or status not in TaskStatus.ALL:
        return jsonify({
            "success": False,
            "error": "Invalid task status"
        }), 400

    return jsonify({
        "success": True,
        "data": {
            "task_id": task_id,
            "status": status
        },
        "message": "Mock response - status not saved"
    }), 200


@api.post("/tasks/<int:task_id>/comments")
def add_comment(task_id):
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify({
            "success": False,
            "error": "JSON object required"
        }), 400

    content = data.get("content")
    if not isinstance(content, str) or not content.strip():
        return jsonify({
            "success": False,
            "error": "Comment content is required"
        }), 400

    return jsonify({
        "success": True,
        "data": {
            "task_id": task_id,
            "content": content.strip()
        },
        "message": "Mock response - comment not saved"
    }), 200
