"""Authentication routes for Enterprise Agent POC.

This module provides Flask routes for user authentication and management.
"""
import logging
from flask import Blueprint, jsonify, request, make_response

from . import auth

LOGGER = logging.getLogger(__name__)

auth_bp = Blueprint("auth", __name__, url_prefix="/api/auth")


@auth_bp.route("/login", methods=["POST"])
def login():
    """User login endpoint.

    Request body:
        username: str
        password: str

    Returns:
        JSON with session token and user info, or error
    """
    payload = request.get_json(force=True)
    username = payload.get("username", "").strip()
    password = payload.get("password", "")

    if not username or not password:
        return jsonify({"error": "請輸入帳號和密碼"}), 400

    user = auth.verify_user(username, password)
    if not user:
        LOGGER.warning(f"Failed login attempt for user: {username}")
        return jsonify({"error": "帳號或密碼錯誤"}), 401

    # Create session
    token = auth.create_session(username)

    LOGGER.info(f"User logged in: {username} (role: {user['role']})")

    response = make_response(jsonify({
        "status": "success",
        "message": "登入成功",
        "user": user,
        "token": token,
    }))

    # Set cookie for browser clients
    response.set_cookie(
        "session_token",
        token,
        httponly=True,
        samesite="Lax",
        max_age=86400,  # 24 hours
    )

    return response


@auth_bp.route("/logout", methods=["POST"])
def logout():
    """User logout endpoint.

    Returns:
        JSON with logout status
    """
    # Get token from header or cookie
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        token = auth_header[7:]
    else:
        token = request.cookies.get("session_token")

    if token:
        auth.invalidate_session(token)

    response = make_response(jsonify({
        "status": "success",
        "message": "已登出",
    }))

    # Clear cookie
    response.delete_cookie("session_token")

    return response


@auth_bp.route("/me", methods=["GET"])
def get_current_user():
    """Get current user info.

    Returns:
        JSON with current user info, or 401 if not logged in
    """
    user = auth.get_current_user()
    if not user:
        return jsonify({"error": "未登入"}), 401

    return jsonify({
        "status": "success",
        "user": user,
    })


@auth_bp.route("/users", methods=["GET"])
@auth.admin_required
def list_users():
    """List all users (admin only).

    Returns:
        JSON with list of users
    """
    users = auth.list_users()
    return jsonify({
        "status": "success",
        "users": users,
    })


@auth_bp.route("/users", methods=["POST"])
@auth.admin_required
def create_user():
    """Create a new user (admin only).

    Request body:
        username: str
        password: str
        role: str (admin or user)
        display_name: str (optional)

    Returns:
        JSON with creation status
    """
    payload = request.get_json(force=True)
    username = payload.get("username", "").strip()
    password = payload.get("password", "")
    role = payload.get("role", "user")
    display_name = payload.get("display_name", "")

    if not username or not password:
        return jsonify({"error": "帳號和密碼為必填"}), 400

    if role not in ["admin", "user"]:
        return jsonify({"error": "角色必須是 admin 或 user"}), 400

    if auth.create_user(username, password, role, display_name):
        LOGGER.info(f"User created: {username} (role: {role})")
        return jsonify({
            "status": "success",
            "message": f"使用者 {username} 已建立",
        })
    else:
        return jsonify({"error": "使用者已存在"}), 409


@auth_bp.route("/users/<username>", methods=["DELETE"])
@auth.admin_required
def delete_user(username: str):
    """Delete a user (admin only).

    Args:
        username: Username to delete

    Returns:
        JSON with deletion status
    """
    # Prevent deleting self
    current_user = auth.get_current_user()
    if current_user and current_user.get("username") == username:
        return jsonify({"error": "無法刪除自己的帳號"}), 400

    if auth.delete_user(username):
        LOGGER.info(f"User deleted: {username}")
        return jsonify({
            "status": "success",
            "message": f"使用者 {username} 已刪除",
        })
    else:
        return jsonify({"error": "使用者不存在"}), 404


@auth_bp.route("/users/<username>/password", methods=["PUT"])
@auth.admin_required
def change_user_password(username: str):
    """Change user password (admin only).

    Args:
        username: Username

    Request body:
        new_password: str

    Returns:
        JSON with change status
    """
    payload = request.get_json(force=True)
    new_password = payload.get("new_password", "")

    if not new_password:
        return jsonify({"error": "新密碼為必填"}), 400

    if auth.change_password(username, new_password):
        LOGGER.info(f"Password changed for user: {username}")
        return jsonify({
            "status": "success",
            "message": f"使用者 {username} 的密碼已更新",
        })
    else:
        return jsonify({"error": "使用者不存在"}), 404


@auth_bp.route("/change-password", methods=["POST"])
@auth.login_required
def change_own_password():
    """Change own password.

    Request body:
        current_password: str
        new_password: str

    Returns:
        JSON with change status
    """
    from flask import g

    payload = request.get_json(force=True)
    current_password = payload.get("current_password", "")
    new_password = payload.get("new_password", "")

    if not current_password or not new_password:
        return jsonify({"error": "請填寫目前密碼和新密碼"}), 400

    username = g.current_user.get("username")

    # Verify current password
    if not auth.verify_user(username, current_password):
        return jsonify({"error": "目前密碼錯誤"}), 401

    if auth.change_password(username, new_password):
        LOGGER.info(f"User changed own password: {username}")
        return jsonify({
            "status": "success",
            "message": "密碼已更新",
        })
    else:
        return jsonify({"error": "無法更新密碼"}), 500
