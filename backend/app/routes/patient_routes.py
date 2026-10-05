from flask import Blueprint, jsonify, request

from app.database import db
from app.utils.auth import role_required, token_required


patient_bp = Blueprint(
    "patient",
    __name__,
    url_prefix="/api/patient",
)

patients_collection = db["patients"]


@patient_bp.post("/profile")
@token_required
@role_required("patient")
def create_patient_profile():
    user_id = request.user.get("user_id")

    data = request.get_json(silent=True) or {}

    date_of_birth = data.get("date_of_birth", "").strip()
    gender = data.get("gender", "").strip()
    blood_group = data.get("blood_group", "").strip()
    emergency_contact = data.get("emergency_contact", "").strip()

    if (
        not date_of_birth
        or not gender
        or not blood_group
        or not emergency_contact
    ):
        return jsonify(
            {
                "success": False,
                "message": (
                    "Date of birth, gender, blood group "
                    "and emergency contact are required"
                ),
            }
        ), 400

    existing_profile = patients_collection.find_one(
        {"user_id": user_id}
    )

    if existing_profile:
        return jsonify(
            {
                "success": False,
                "message": "Patient profile already exists",
            }
        ), 409

    patient = {
        "user_id": user_id,
        "date_of_birth": date_of_birth,
        "gender": gender,
        "blood_group": blood_group,
        "emergency_contact": emergency_contact,
    }

    result = patients_collection.insert_one(patient)

    return jsonify(
        {
            "success": True,
            "message": "Patient profile created successfully",
            "profile": {
                "id": str(result.inserted_id),
                "user_id": user_id,
                "date_of_birth": date_of_birth,
                "gender": gender,
                "blood_group": blood_group,
                "emergency_contact": emergency_contact,
            },
        }
    ), 201


@patient_bp.get("/profile")
@token_required
@role_required("patient")
def get_patient_profile():
    user_id = request.user.get("user_id")

    profile = patients_collection.find_one(
        {"user_id": user_id}
    )

    if not profile:
        return jsonify(
            {
                "success": False,
                "message": "Patient profile not found",
            }
        ), 404

    return jsonify(
        {
            "success": True,
            "profile": {
                "id": str(profile["_id"]),
                "user_id": profile["user_id"],
                "date_of_birth": profile["date_of_birth"],
                "gender": profile["gender"],
                "blood_group": profile["blood_group"],
                "emergency_contact": profile["emergency_contact"],
            },
        }
    ), 200