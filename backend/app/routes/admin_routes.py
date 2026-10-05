from flask import Blueprint, jsonify, request
from pymongo.errors import DuplicateKeyError

from app.database import db
from app.utils.auth import (
    hash_password,
    role_required,
    token_required,
)


admin_bp = Blueprint(
    "admin",
    __name__,
    url_prefix="/api/admin",
)

users_collection = db["users"]
patients = db["patients"]
doctors_collection = db["doctors"]


@admin_bp.get("/dashboard")
@token_required
@role_required("admin")
def get_admin_dashboard():
    total_users = users_collection.count_documents({})

    total_patients = users_collection.count_documents(
        {"role": "patient"}
    )

    total_doctors = users_collection.count_documents(
        {"role": "doctor"}
    )

    total_admins = users_collection.count_documents(
        {"role": "admin"}
    )

    total_receptionists = users_collection.count_documents(
        {"role": "receptionist"}
    )

    total_patient_profiles = patients.count_documents({})

    total_doctor_profiles = doctors_collection.count_documents({})

    return jsonify(
        {
            "success": True,
            "dashboard": {
                "total_users": total_users,
                "total_patients": total_patients,
                "total_doctors": total_doctors,
                "total_admins": total_admins,
                "total_receptionists": total_receptionists,
                "total_patient_profiles": total_patient_profiles,
                "total_doctor_profiles": total_doctor_profiles,
            },
        }
    ), 200


@admin_bp.get("/users")
@token_required
@role_required("admin")
def get_all_users():
    users = users_collection.find(
        {},
        {
            "password_hash": 0,
        },
    ).sort(
        "_id",
        1,
    )

    user_list = []

    for user in users:
        user_list.append(
            {
                "id": str(user["_id"]),
                "name": user.get("name", ""),
                "email": user.get("email", ""),
                "role": user.get("role", ""),
            }
        )

    return jsonify(
        {
            "success": True,
            "users": user_list,
            "count": len(user_list),
        }
    ), 200


@admin_bp.post("/doctors")
@token_required
@role_required("admin")
def create_doctor():
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

    doctor = {
        "name": name,
        "email": email,
        "password_hash": hash_password(password),
        "role": "doctor",
    }

    try:
        result = users_collection.insert_one(doctor)

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
            "message": "Doctor account created successfully",
            "user": {
                "id": str(result.inserted_id),
                "name": name,
                "email": email,
                "role": "doctor",
            },
        }
    ), 201


@admin_bp.post("/receptionists")
@token_required
@role_required("admin")
def create_receptionist():
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

    receptionist = {
        "name": name,
        "email": email,
        "password_hash": hash_password(password),
        "role": "receptionist",
    }

    try:
        result = users_collection.insert_one(receptionist)

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
            "message": "Receptionist account created successfully",
            "user": {
                "id": str(result.inserted_id),
                "name": name,
                "email": email,
                "role": "receptionist",
            },
        }
    ), 201