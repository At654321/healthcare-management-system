from bson import ObjectId
from flask import Blueprint, jsonify, request

from app.database import db
from app.utils.auth import role_required, token_required


doctor_bp = Blueprint(
    "doctor",
    __name__,
    url_prefix="/api/doctor",
)

doctors_collection = db["doctors"]
users_collection = db["users"]
patients_collection = db["patients"]
appointments_collection = db["appointments"]
medical_records_collection = db["medical_records"]


@doctor_bp.post("/profile")
@token_required
@role_required("doctor")
def create_doctor_profile():
    user_id = request.user.get("user_id")

    data = request.get_json(silent=True) or {}

    specialization = data.get(
        "specialization",
        "",
    ).strip()

    license_number = data.get(
        "license_number",
        "",
    ).strip()

    hospital = data.get(
        "hospital",
        "",
    ).strip()

    if (
        not specialization
        or not license_number
        or not hospital
    ):
        return jsonify(
            {
                "success": False,
                "message": (
                    "Specialization, license number "
                    "and hospital are required"
                ),
            }
        ), 400

    existing_profile = doctors_collection.find_one(
        {
            "user_id": user_id,
        }
    )

    if existing_profile:
        return jsonify(
            {
                "success": False,
                "message": "Doctor profile already exists",
            }
        ), 409

    doctor = {
        "user_id": user_id,
        "specialization": specialization,
        "license_number": license_number,
        "hospital": hospital,
    }

    result = doctors_collection.insert_one(
        doctor
    )

    return jsonify(
        {
            "success": True,
            "message": "Doctor profile created successfully",
            "profile": {
                "id": str(result.inserted_id),
                "user_id": user_id,
                "specialization": specialization,
                "license_number": license_number,
                "hospital": hospital,
            },
        }
    ), 201


@doctor_bp.get("/profile")
@token_required
@role_required("doctor")
def get_doctor_profile():
    user_id = request.user.get("user_id")

    profile = doctors_collection.find_one(
        {
            "user_id": user_id,
        }
    )

    if not profile:
        return jsonify(
            {
                "success": False,
                "message": "Doctor profile not found",
            }
        ), 404

    doctor_user = users_collection.find_one(
        {
            "_id": ObjectId(user_id),
            "role": "doctor",
        }
    )

    return jsonify(
        {
            "success": True,
            "profile": {
                "id": str(profile["_id"]),
                "user_id": profile["user_id"],
                "name": (
                    doctor_user.get("name", "")
                    if doctor_user
                    else ""
                ),
                "email": (
                    doctor_user.get("email", "")
                    if doctor_user
                    else ""
                ),
                "specialization": profile[
                    "specialization"
                ],
                "license_number": profile[
                    "license_number"
                ],
                "hospital": profile["hospital"],
            },
        }
    ), 200


def serialize_datetime(value):
    if hasattr(value, "isoformat"):
        return value.isoformat()

    return value


@doctor_bp.get("/patients/<patient_id>")
@token_required
@role_required("doctor")
def get_patient_details(patient_id):
    """
    Get complete patient details for a doctor.

    Doctor can access a patient only when there is
    an appointment relationship between them.
    """

    doctor_user_id = request.user.get("user_id")

    try:
        patient_object_id = ObjectId(
            patient_id
        )

    except Exception:
        return jsonify(
            {
                "success": False,
                "message": "Invalid patient ID",
            }
        ), 400

    # -------------------------------------------------
    # Find patient account
    # -------------------------------------------------

    patient_user = users_collection.find_one(
        {
            "_id": patient_object_id,
            "role": "patient",
        }
    )

    if not patient_user:
        return jsonify(
            {
                "success": False,
                "message": "Patient not found",
            }
        ), 404

    patient_user_id = str(
        patient_user["_id"]
    )

    # -------------------------------------------------
    # Check doctor-patient relationship
    # -------------------------------------------------

    doctor_appointment = (
        appointments_collection.find_one(
            {
                "doctor_id": doctor_user_id,
                "patient_id": patient_user_id,
            }
        )
    )

    if not doctor_appointment:
        return jsonify(
            {
                "success": False,
                "message": (
                    "You do not have access to "
                    "this patient"
                ),
            }
        ), 403

    # -------------------------------------------------
    # Patient profile
    # -------------------------------------------------

    patient_profile = patients_collection.find_one(
        {
            "user_id": patient_user_id,
        }
    )

    profile_data = None

    if patient_profile:
        profile_data = {
            "id": str(
                patient_profile["_id"]
            ),
            "user_id": patient_user_id,
            "date_of_birth": patient_profile.get(
                "date_of_birth",
                "",
            ),
            "gender": patient_profile.get(
                "gender",
                "",
            ),
            "blood_group": patient_profile.get(
                "blood_group",
                "",
            ),
            "emergency_contact": patient_profile.get(
                "emergency_contact",
                "",
            ),
        }

    # -------------------------------------------------
    # All appointments of this patient with doctor
    # -------------------------------------------------

    appointments = appointments_collection.find(
        {
            "doctor_id": doctor_user_id,
            "patient_id": patient_user_id,
        }
    ).sort(
        "appointment_date",
        -1,
    )

    appointment_list = []

    for appointment in appointments:
        appointment_list.append(
            {
                "id": str(
                    appointment["_id"]
                ),
                "appointment_date": serialize_datetime(
                    appointment.get(
                        "appointment_date"
                    )
                ),
                "reason": appointment.get(
                    "reason",
                    "",
                ),
                "status": appointment.get(
                    "status",
                    "pending",
                ),
            }
        )

    # -------------------------------------------------
    # Patient medical records
    # -------------------------------------------------

    medical_records = (
        medical_records_collection.find(
            {
                "patient_id": patient_user_id,
            }
        ).sort(
            "created_at",
            -1,
        )
    )

    medical_record_list = []

    for record in medical_records:
        medical_record_list.append(
            {
                "id": str(
                    record["_id"]
                ),
                "appointment_id": record.get(
                    "appointment_id",
                    "",
                ),
                "doctor_id": record.get(
                    "doctor_id",
                    "",
                ),
                "diagnosis": record.get(
                    "diagnosis",
                    "",
                ),
                "medicines": record.get(
                    "medicines",
                    [],
                ),
                "instructions": record.get(
                    "instructions",
                    "",
                ),
                "created_at": serialize_datetime(
                    record.get(
                        "created_at"
                    )
                ),
            }
        )

    # -------------------------------------------------
    # Final response
    # -------------------------------------------------

    return jsonify(
        {
            "success": True,
            "patient": {
                "id": patient_user_id,
                "name": patient_user.get(
                    "name",
                    "",
                ),
                "email": patient_user.get(
                    "email",
                    "",
                ),
                "role": patient_user.get(
                    "role",
                    "",
                ),
                "profile": profile_data,
                "appointments": appointment_list,
                "medical_records": medical_record_list,
            },
        }
    ), 200