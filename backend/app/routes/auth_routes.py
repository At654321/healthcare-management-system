from bson import ObjectId
from flask import Blueprint, jsonify, request
from pymongo.errors import DuplicateKeyError

from app.database import db
from app.utils.auth import (
    create_access_token,
    hash_password,
    token_required,
    verify_password,
)


auth_bp = Blueprint(
    "auth",
    __name__,
    url_prefix="/api/auth",
)

users_collection = db["users"]


@auth_bp.post("/register")
def register():
    data = request.get_json(silent=True) or {}

    name = data.get("name", "").strip()
    email = data.get("email", "").strip().lower()
    password = data.get("password", "").strip()

    if not name or not email or not password:
        return jsonify(
            {
                "success": False,
                "message": "Name, email and password are required",
            }
        ), 400

    if len(password) < 6:
        return jsonify(
            {
                "success": False,
                "message": "Password must be at least 6 characters long",
            }
        ), 400

    existing_user = users_collection.find_one(
        {"email": email}
    )

    if existing_user:
        return jsonify(
            {
                "success": False,
                "message": "Email is already registered",
            }
        ), 409

    password_hash = hash_password(password)

    user = {
        "name": name,
        "email": email,
        "password_hash": password_hash,
        "role": "patient",
    }

    try:
        result = users_collection.insert_one(user)

    except DuplicateKeyError:
        return jsonify(
            {
                "success": False,
                "message": "Email is already registered",
            }
        ), 409

    return jsonify(
        {
            "success": True,
            "message": "Registration successful",
            "user": {
                "id": str(result.inserted_id),
                "name": name,
                "email": email,
                "role": "patient",
            },
        }
    ), 201


@auth_bp.post("/login")
def login():
    data = request.get_json(silent=True) or {}

    email = data.get("email", "").strip().lower()
    password = data.get("password", "").strip()

    if not email or not password:
        return jsonify(
            {
                "success": False,
                "message": "Email and password are required",
            }
        ), 400

    user = users_collection.find_one(
        {"email": email}
    )

    if not user:
        return jsonify(
            {
                "success": False,
                "message": "Invalid email or password",
            }
        ), 401

    password_is_valid = verify_password(
        password,
        user["password_hash"],
    )

    if not password_is_valid:
        return jsonify(
            {
                "success": False,
                "message": "Invalid email or password",
            }
        ), 401

    token = create_access_token(
        user_id=str(user["_id"]),
        role=user["role"],
    )

    return jsonify(
        {
            "success": True,
            "message": "Login successful",
            "token": token,
            "user": {
                "id": str(user["_id"]),
                "name": user["name"],
                "email": user["email"],
                "role": user["role"],
            },
        }
    ), 200


@auth_bp.get("/me")
@token_required
def get_current_user():
    user_id = request.user.get("user_id")

    try:
        object_id = ObjectId(user_id)

    except Exception:
        return jsonify(
            {
                "success": False,
                "message": "Invalid user ID",
            }
        ), 400

    user = users_collection.find_one(
        {"_id": object_id}
    )

    if not user:
        return jsonify(
            {
                "success": False,
                "message": "User not found",
            }
        ), 404

    return jsonify(
        {
            "success": True,
            "user": {
                "id": str(user["_id"]),
                "name": user["name"],
                "email": user["email"],
                "role": user["role"],
            },
        }
    ), 200