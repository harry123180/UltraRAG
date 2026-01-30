"""Authentication module for Enterprise Agent POC.

This module provides user authentication, session management, and role-based access control.
"""
import hashlib
import json
import os
import secrets
from datetime import datetime, timedelta
from functools import wraps
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from flask import g, jsonify, request, session

# Data directory for storing user data
DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data"
USERS_FILE = DATA_DIR / "users.json"
SESSIONS_FILE = DATA_DIR / "sessions.json"


def _hash_password(password: str, salt: Optional[str] = None) -> tuple:
    """Hash password with salt using SHA-256.

    Args:
        password: Plain text password
        salt: Optional salt (generated if not provided)

    Returns:
        Tuple of (hashed_password, salt)
    """
    if salt is None:
        salt = secrets.token_hex(16)
    hashed = hashlib.sha256(f"{salt}{password}".encode()).hexdigest()
    return hashed, salt


def _load_users() -> Dict[str, Any]:
    """Load users from JSON file.

    Returns:
        Dictionary of users
    """
    if not USERS_FILE.exists():
        # Create default admin user
        default_users = _create_default_users()
        _save_users(default_users)
        return default_users

    try:
        with open(USERS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return _create_default_users()


def _save_users(users: Dict[str, Any]) -> None:
    """Save users to JSON file.

    Args:
        users: Dictionary of users
    """
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with open(USERS_FILE, "w", encoding="utf-8") as f:
        json.dump(users, f, indent=2, ensure_ascii=False)


def _create_default_users() -> Dict[str, Any]:
    """Create default admin and user accounts.

    Returns:
        Dictionary with default users
    """
    admin_hash, admin_salt = _hash_password("admin123")
    user_hash, user_salt = _hash_password("user123")

    return {
        "admin": {
            "password_hash": admin_hash,
            "salt": admin_salt,
            "role": "admin",
            "display_name": "系統管理員",
            "created_at": datetime.now().isoformat(),
        },
        "user": {
            "password_hash": user_hash,
            "salt": user_salt,
            "role": "user",
            "display_name": "一般使用者",
            "created_at": datetime.now().isoformat(),
        },
    }


def _load_sessions() -> Dict[str, Any]:
    """Load sessions from JSON file.

    Returns:
        Dictionary of sessions
    """
    if not SESSIONS_FILE.exists():
        return {}

    try:
        with open(SESSIONS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def _save_sessions(sessions: Dict[str, Any]) -> None:
    """Save sessions to JSON file.

    Args:
        sessions: Dictionary of sessions
    """
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with open(SESSIONS_FILE, "w", encoding="utf-8") as f:
        json.dump(sessions, f, indent=2, ensure_ascii=False)


def verify_user(username: str, password: str) -> Optional[Dict[str, Any]]:
    """Verify user credentials.

    Args:
        username: Username
        password: Plain text password

    Returns:
        User dict if valid, None otherwise
    """
    users = _load_users()
    user = users.get(username)

    if not user:
        return None

    hashed, _ = _hash_password(password, user["salt"])
    if hashed == user["password_hash"]:
        return {
            "username": username,
            "role": user["role"],
            "display_name": user.get("display_name", username),
        }
    return None


def create_session(username: str) -> str:
    """Create a new session for user.

    Args:
        username: Username

    Returns:
        Session token
    """
    sessions = _load_sessions()
    token = secrets.token_urlsafe(32)

    users = _load_users()
    user = users.get(username, {})

    sessions[token] = {
        "username": username,
        "role": user.get("role", "user"),
        "display_name": user.get("display_name", username),
        "created_at": datetime.now().isoformat(),
        "expires_at": (datetime.now() + timedelta(hours=24)).isoformat(),
    }

    _save_sessions(sessions)
    return token


def validate_session(token: str) -> Optional[Dict[str, Any]]:
    """Validate session token.

    Args:
        token: Session token

    Returns:
        Session data if valid, None otherwise
    """
    if not token:
        return None

    sessions = _load_sessions()
    session_data = sessions.get(token)

    if not session_data:
        return None

    # Check expiration
    expires_at = datetime.fromisoformat(session_data["expires_at"])
    if datetime.now() > expires_at:
        # Remove expired session
        del sessions[token]
        _save_sessions(sessions)
        return None

    return session_data


def invalidate_session(token: str) -> bool:
    """Invalidate session token (logout).

    Args:
        token: Session token

    Returns:
        True if session was invalidated
    """
    sessions = _load_sessions()
    if token in sessions:
        del sessions[token]
        _save_sessions(sessions)
        return True
    return False


def get_current_user() -> Optional[Dict[str, Any]]:
    """Get current user from request.

    Returns:
        Current user dict or None
    """
    # Check Authorization header
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        token = auth_header[7:]
        return validate_session(token)

    # Check cookie
    token = request.cookies.get("session_token")
    if token:
        return validate_session(token)

    return None


def login_required(f: Callable) -> Callable:
    """Decorator to require login for route.

    Args:
        f: Route function

    Returns:
        Wrapped function
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        user = get_current_user()
        if not user:
            return jsonify({"error": "Unauthorized", "message": "請先登入"}), 401
        g.current_user = user
        return f(*args, **kwargs)
    return decorated_function


def admin_required(f: Callable) -> Callable:
    """Decorator to require admin role for route.

    Args:
        f: Route function

    Returns:
        Wrapped function
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        user = get_current_user()
        if not user:
            return jsonify({"error": "Unauthorized", "message": "請先登入"}), 401
        if user.get("role") != "admin":
            return jsonify({"error": "Forbidden", "message": "需要管理員權限"}), 403
        g.current_user = user
        return f(*args, **kwargs)
    return decorated_function


def create_user(
    username: str,
    password: str,
    role: str = "user",
    display_name: Optional[str] = None,
) -> bool:
    """Create a new user.

    Args:
        username: Username
        password: Plain text password
        role: User role ('admin' or 'user')
        display_name: Display name

    Returns:
        True if user created successfully
    """
    users = _load_users()

    if username in users:
        return False

    password_hash, salt = _hash_password(password)
    users[username] = {
        "password_hash": password_hash,
        "salt": salt,
        "role": role,
        "display_name": display_name or username,
        "created_at": datetime.now().isoformat(),
    }

    _save_users(users)
    return True


def delete_user(username: str) -> bool:
    """Delete a user.

    Args:
        username: Username to delete

    Returns:
        True if user deleted successfully
    """
    users = _load_users()

    if username not in users:
        return False

    del users[username]
    _save_users(users)
    return True


def list_users() -> List[Dict[str, Any]]:
    """List all users (without password info).

    Returns:
        List of user dicts
    """
    users = _load_users()
    result = []

    for username, data in users.items():
        result.append({
            "username": username,
            "role": data.get("role", "user"),
            "display_name": data.get("display_name", username),
            "created_at": data.get("created_at", ""),
        })

    return result


def change_password(username: str, new_password: str) -> bool:
    """Change user password.

    Args:
        username: Username
        new_password: New plain text password

    Returns:
        True if password changed successfully
    """
    users = _load_users()

    if username not in users:
        return False

    password_hash, salt = _hash_password(new_password)
    users[username]["password_hash"] = password_hash
    users[username]["salt"] = salt

    _save_users(users)
    return True
