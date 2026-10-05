from datetime import datetime, timezone

from bson import ObjectId
from flask import Blueprint, jsonify, request

from app.database import db
from app.utils.auth import role_required, token_required


appointment_bp = Blueprint(
    "appointment",
    __name__,
    url_prefix="/api/appointments",
)

appointments_collection = db["appointments"]
users_collection = db["users"]
patients_collection = db["patients"]
doctors_collection = db["doctors"]


@appointment_bp.post("")
@token_required
@role_required("patient")
def create_appointment():
    patient_user_id = request.user.get("user_id")

    data = request.get_json(silent=True) or {}

    doctor_user_id = data.get("doctor_id", "").strip()
    appointment_date = data.get("appointment_date", "").strip()
    reason = data.get("reason", "").strip()

    if not doctor_user_id or not appointment_date:
        return jsonify(
            {
                "success": False,
                "message": (
                    "Doctor ID and appointment date "
                    "are required"
                ),
            }
        ), 400

    try:
        doctor_object_id = ObjectId(doctor_user_id)

    except Exception:
        return jsonify(
            {
                "success": False,
                "message": "Invalid doctor ID",
            }
        ), 400

    doctor_user = users_collection.find_one(
        {
            "_id": doctor_object_id,
            "role": "doctor",
        }
    )

    if not doctor_user:
        return jsonify(
            {
                "success": False,
                "message": "Doctor not found",
            }
        ), 404

    doctor_profile = doctors_collection.find_one(
        {
            "user_id": doctor_user_id,
        }
    )

    if not doctor_profile:
        return jsonify(
            {
                "success": False,
                "message": "Doctor profile not found",
            }
        ), 404

    patient_profile = patients_collection.find_one(
        {
            "user_id": patient_user_id,
        }
    )

    if not patient_profile:
        return jsonify(
            {
                "success": False,
                "message": "Please create your patient profile first",
            }
        ), 404

    try:
        appointment_datetime = datetime.fromisoformat(
            appointment_date.replace("Z", "+00:00")
        )

    except ValueError:
        return jsonify(
            {
                "success": False,
                "message": (
                    "Invalid appointment date format. "
                    "Use ISO format such as "
                    "2026-10-10T10:30:00"
                ),
            }
        ), 400

    if appointment_datetime.tzinfo is None:
        appointment_datetime = appointment_datetime.replace(
            tzinfo=timezone.utc
        )

    appointment = {
        "patient_id": patient_user_id,
        "doctor_id": doctor_user_id,
        "appointment_date": appointment_datetime,
        "reason": reason,
        "status": "pending",
        "created_at": datetime.now(timezone.utc),
    }

    result = appointments_collection.insert_one(
        appointment
    )

    return jsonify(
        {
            "success": True,
            "message": "Appointment created successfully",
            "appointment": {
                "id": str(result.inserted_id),
                "patient_id": patient_user_id,
                "doctor_id": doctor_user_id,
                "appointment_date": appointment_datetime.isoformat(),
                "reason": reason,
                "status": "pending",
            },
        }
    ), 201


@appointment_bp.get("/patient")
@token_required
@role_required("patient")
def get_patient_appointments():
    patient_user_id = request.user.get("user_id")

    appointments = appointments_collection.find(
        {
            "patient_id": patient_user_id,
        }
    ).sort(
        "appointment_date",
        1,
    )

    appointment_list = []

    for appointment in appointments:
        appointment_list.append(
            {
                "id": str(appointment["_id"]),
                "patient_id": appointment["patient_id"],
                "doctor_id": appointment["doctor_id"],
                "appointment_date": appointment[
                    "appointment_date"
                ].isoformat(),
                "reason": appointment.get("reason", ""),
                "status": appointment.get(
                    "status",
                    "pending",
                ),
            }
        )

    return jsonify(
        {
            "success": True,
            "appointments": appointment_list,
            "count": len(appointment_list),
        }
    ), 200


@appointment_bp.get("/doctor")
@token_required
@role_required("doctor")
def get_doctor_appointments():
    doctor_user_id = request.user.get("user_id")

    appointments = appointments_collection.find(
        {
            "doctor_id": doctor_user_id,
        }
    ).sort(
        "appointment_date",
        1,
    )

    appointment_list = []

    for appointment in appointments:
        appointment_list.append(
            {
                "id": str(appointment["_id"]),
                "patient_id": appointment["patient_id"],
                "doctor_id": appointment["doctor_id"],
                "appointment_date": appointment[
                    "appointment_date"
                ].isoformat(),
                "reason": appointment.get("reason", ""),
                "status": appointment.get(
                    "status",
                    "pending",
                ),
            }
        )

    return jsonify(
        {
            "success": True,
            "appointments": appointment_list,
            "count": len(appointment_list),
        }
    ), 200


@appointment_bp.patch("/<appointment_id>/status")
@token_required
@role_required("doctor")
def update_appointment_status(appointment_id):
    doctor_user_id = request.user.get("user_id")

    try:
        appointment_object_id = ObjectId(appointment_id)

    except Exception:
        return jsonify(
            {
                "success": False,
                "message": "Invalid appointment ID",
            }
        ), 400

    data = request.get_json(silent=True) or {}

    new_status = data.get("status", "").strip().lower()

    allowed_statuses = {
        "confirmed",
        "rejected",
        "completed",
    }

    if new_status not in allowed_statuses:
        return jsonify(
            {
                "success": False,
                "message": (
                    "Invalid status. Allowed values are "
                    "confirmed, rejected and completed"
                ),
            }
        ), 400

    appointment = appointments_collection.find_one(
        {
            "_id": appointment_object_id,
            "doctor_id": doctor_user_id,
        }
    )

    if not appointment:
        return jsonify(
            {
                "success": False,
                "message": "Appointment not found",
            }
        ), 404

    current_status = appointment.get(
        "status",
        "pending",
    )

    valid_transitions = {
        "pending": {
            "confirmed",
            "rejected",
        },
        "confirmed": {
            "completed",
        },
        "rejected": set(),
        "completed": set(),
    }

    if new_status not in valid_transitions.get(
        current_status,
        set(),
    ):
        return jsonify(
            {
                "success": False,
                "message": (
                    f"Cannot change appointment status "
                    f"from {current_status} to {new_status}"
                ),
            }
        ), 400

    appointments_collection.update_one(
        {
            "_id": appointment_object_id,
            "doctor_id": doctor_user_id,
        },
        {
            "$set": {
                "status": new_status,
                "updated_at": datetime.now(timezone.utc),
            }
        },
    )

    return jsonify(
        {
            "success": True,
            "message": "Appointment status updated successfully",
            "appointment": {
                "id": str(appointment["_id"]),
                "patient_id": appointment["patient_id"],
                "doctor_id": appointment["doctor_id"],
                "appointment_date": appointment[
                    "appointment_date"
                ].isoformat(),
                "reason": appointment.get(
                    "reason",
                    "",
                ),
                "status": new_status,
            },
        }
    ), 200