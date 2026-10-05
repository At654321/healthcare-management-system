from datetime import datetime, timedelta, timezone
from functools import wraps

import bcrypt
import jwt
from flask import jsonify, request

from app.config import Config


def hash_password(password: str) -> str:
    """Hash a plain-text password using bcrypt."""
    password_bytes = password.encode("utf-8")

    hashed_password = bcrypt.hashpw(
        password_bytes,
        bcrypt.gensalt(),
    )

    return hashed_password.decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    """Verify a plain-text password against a bcrypt hash."""
    password_bytes = password.encode("utf-8")
    hashed_password_bytes = password_hash.encode("utf-8")

    return bcrypt.checkpw(
        password_bytes,
        hashed_password_bytes,
    )


def create_access_token(user_id: str, role: str) -> str:
    """Create a JWT access token."""
    now = datetime.now(timezone.utc)

    payload = {
        "user_id": user_id,
        "role": role,
        "iat": now,
        "exp": now + timedelta(days=1),
    }

    token = jwt.encode(
        payload,
        Config.JWT_SECRET,
        algorithm="HS256",
    )

    return token


def decode_access_token(token: str) -> dict:
    """Decode and validate a JWT access token."""
    return jwt.decode(
        token,
        Config.JWT_SECRET,
        algorithms=["HS256"],
    )


def token_required(f):
    """Protect an API route using JWT authentication."""

    @wraps(f)
    def decorated(*args, **kwargs):
        auth_header = request.headers.get("Authorization")

        if not auth_header:
            return jsonify(
                {
                    "success": False,
                    "message": "Authorization token is required",
                }
            ), 401

        parts = auth_header.split()

        if len(parts) != 2 or parts[0].lower() != "bearer":
            return jsonify(
                {
                    "success": False,
                    "message": "Authorization header must use Bearer token",
                }
            ), 401

        token = parts[1]

        try:
            payload = decode_access_token(token)

        except jwt.ExpiredSignatureError:
            return jsonify(
                {
                    "success": False,
                    "message": "Token has expired",
                }
            ), 401

        except jwt.InvalidTokenError:
            return jsonify(
                {
                    "success": False,
                    "message": "Invalid token",
                }
            ), 401

        request.user = payload

        return f(*args, **kwargs)

    return decorated


def role_required(*allowed_roles):
    """
    Allow access only to users having one of the specified roles.

    Example:
        @role_required("doctor")
        @role_required("admin", "doctor")
    """

    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            user = getattr(request, "user", None)

            if not user:
                return jsonify(
                    {
                        "success": False,
                        "message": "Authentication is required",
                    }
                ), 401

            user_role = user.get("role")

            if user_role not in allowed_roles:
                return jsonify(
                    {
                        "success": False,
                        "message": "You do not have permission to access this resource",
                    }
                ), 403

            return f(*args, **kwargs)

        return decorated

    return decorator