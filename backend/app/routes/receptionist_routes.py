from datetime import datetime, timezone

from bson import ObjectId
from flask import Blueprint, jsonify, request
from pymongo.errors import DuplicateKeyError

from app.database import db
from app.utils.auth import (
    hash_password,
    role_required,
    token_required,
)


receptionist_bp = Blueprint(
    "receptionist",
    __name__,
    url_prefix="/api/receptionist",
)


users_collection = db["users"]
patients_collection = db["patients"]
doctors_collection = db["doctors"]
appointments_collection = db["appointments"]


# ============================================================
# CREATE PATIENT ACCOUNT
# ============================================================

@receptionist_bp.post("/patients")
@token_required
@role_required("receptionist")
def create_patient_account():

    data = request.get_json(silent=True) or {}

    name = data.get("name", "").strip()
    email = data.get("email", "").strip().lower()
    password = data.get("password", "").strip()

    if not name or not email or not password:
        return jsonify({
            "success": False,
            "message": "Name, email and password are required",
        }), 400

    if len(password) < 6:
        return jsonify({
            "success": False,
            "message": "Password must be at least 6 characters long",
        }), 400

    existing_user = users_collection.find_one({
        "email": email
    })

    if existing_user:
        return jsonify({
            "success": False,
            "message": "Email is already registered",
        }), 409

    patient = {
        "name": name,
        "email": email,
        "password_hash": hash_password(password),
        "role": "patient",
    }

    try:
        result = users_collection.insert_one(patient)

    except DuplicateKeyError:
        return jsonify({
            "success": False,
            "message": "Email is already registered",
        }), 409

    return jsonify({
        "success": True,
        "message": "Patient account created successfully",
        "user": {
            "id": str(result.inserted_id),
            "name": name,
            "email": email,
            "role": "patient",
        },
    }), 201


# ============================================================
# GET ALL PATIENTS
# ============================================================

@receptionist_bp.get("/patients")
@token_required
@role_required("receptionist")
def get_all_patients():

    patients = users_collection.find(
        {
            "role": "patient"
        },
        {
            "password_hash": 0
        }
    ).sort("_id", 1)

    patient_list = []

    for patient in patients:

        profile = patients_collection.find_one({
            "user_id": str(patient["_id"])
        })

        patient_data = {
            "id": str(patient["_id"]),
            "name": patient.get("name", ""),
            "email": patient.get("email", ""),
            "role": patient.get("role", "patient"),
        }

        if profile:
            patient_data["profile"] = {
                "id": str(profile["_id"]),
                "date_of_birth": profile.get(
                    "date_of_birth",
                    ""
                ),
                "gender": profile.get(
                    "gender",
                    ""
                ),
                "blood_group": profile.get(
                    "blood_group",
                    ""
                ),
                "emergency_contact": profile.get(
                    "emergency_contact",
                    ""
                ),
            }
        else:
            patient_data["profile"] = None

        patient_list.append(patient_data)

    return jsonify({
        "success": True,
        "patients": patient_list,
        "count": len(patient_list),
    }), 200


# ============================================================
# GET SINGLE PATIENT
# ============================================================

@receptionist_bp.get("/patients/<patient_id>")
@token_required
@role_required("receptionist")
def get_single_patient(patient_id):

    try:
        patient_object_id = ObjectId(patient_id)

    except Exception:
        return jsonify({
            "success": False,
            "message": "Invalid patient ID",
        }), 400

    patient = users_collection.find_one(
        {
            "_id": patient_object_id,
            "role": "patient",
        },
        {
            "password_hash": 0
        }
    )

    if not patient:
        return jsonify({
            "success": False,
            "message": "Patient not found",
        }), 404

    profile = patients_collection.find_one({
        "user_id": patient_id
    })

    patient_data = {
        "id": str(patient["_id"]),
        "name": patient.get("name", ""),
        "email": patient.get("email", ""),
        "role": patient.get("role", "patient"),
    }

    if profile:
        patient_data["profile"] = {
            "id": str(profile["_id"]),
            "date_of_birth": profile.get(
                "date_of_birth",
                ""
            ),
            "gender": profile.get(
                "gender",
                ""
            ),
            "blood_group": profile.get(
                "blood_group",
                ""
            ),
            "emergency_contact": profile.get(
                "emergency_contact",
                ""
            ),
        }
    else:
        patient_data["profile"] = None

    return jsonify({
        "success": True,
        "patient": patient_data,
    }), 200


# ============================================================
# GET ALL DOCTORS
# ============================================================

@receptionist_bp.get("/doctors")
@token_required
@role_required("receptionist")
def get_all_doctors():

    doctors = users_collection.find(
        {
            "role": "doctor"
        },
        {
            "password_hash": 0
        }
    ).sort("_id", 1)

    doctor_list = []

    for doctor in doctors:

        profile = doctors_collection.find_one({
            "user_id": str(doctor["_id"])
        })

        doctor_data = {
            "id": str(doctor["_id"]),
            "name": doctor.get("name", ""),
            "email": doctor.get("email", ""),
            "role": doctor.get("role", "doctor"),
        }

        if profile:
            doctor_data["profile"] = {
                "id": str(profile["_id"]),
                "specialization": profile.get(
                    "specialization",
                    ""
                ),
                "license_number": profile.get(
                    "license_number",
                    ""
                ),
                "hospital": profile.get(
                    "hospital",
                    ""
                ),
            }
        else:
            doctor_data["profile"] = None

        doctor_list.append(doctor_data)

    return jsonify({
        "success": True,
        "doctors": doctor_list,
        "count": len(doctor_list),
    }), 200


# ============================================================
# CREATE APPOINTMENT
# ============================================================

@receptionist_bp.post("/appointments")
@token_required
@role_required("receptionist")
def create_appointment():

    data = request.get_json(silent=True) or {}

    patient_id = data.get(
        "patient_id",
        ""
    ).strip()

    doctor_id = data.get(
        "doctor_id",
        ""
    ).strip()

    appointment_date = data.get(
        "appointment_date",
        ""
    ).strip()

    reason = data.get(
        "reason",
        ""
    ).strip()

    # --------------------------------------------------------
    # Validate required fields
    # --------------------------------------------------------

    if not patient_id or not doctor_id or not appointment_date:
        return jsonify({
            "success": False,
            "message": (
                "Patient ID, doctor ID and appointment "
                "date are required"
            ),
        }), 400

    # --------------------------------------------------------
    # Validate patient ID
    # --------------------------------------------------------

    try:
        patient_object_id = ObjectId(patient_id)

    except Exception:
        return jsonify({
            "success": False,
            "message": "Invalid patient ID",
        }), 400

    # --------------------------------------------------------
    # Validate doctor ID
    # --------------------------------------------------------

    try:
        doctor_object_id = ObjectId(doctor_id)

    except Exception:
        return jsonify({
            "success": False,
            "message": "Invalid doctor ID",
        }), 400

    # --------------------------------------------------------
    # Check patient
    # --------------------------------------------------------

    patient = users_collection.find_one(
        {
            "_id": patient_object_id,
            "role": "patient",
        },
        {
            "password_hash": 0
        }
    )

    if not patient:
        return jsonify({
            "success": False,
            "message": "Patient not found",
        }), 404

    # --------------------------------------------------------
    # Check patient profile
    # --------------------------------------------------------

    patient_profile = patients_collection.find_one({
        "user_id": patient_id
    })

    if not patient_profile:
        return jsonify({
            "success": False,
            "message": "Patient profile not found",
        }), 404

    # --------------------------------------------------------
    # Check doctor
    # --------------------------------------------------------

    doctor = users_collection.find_one(
        {
            "_id": doctor_object_id,
            "role": "doctor",
        },
        {
            "password_hash": 0
        }
    )

    if not doctor:
        return jsonify({
            "success": False,
            "message": "Doctor not found",
        }), 404

    # --------------------------------------------------------
    # Check doctor profile
    # --------------------------------------------------------

    doctor_profile = doctors_collection.find_one({
        "user_id": doctor_id
    })

    if not doctor_profile:
        return jsonify({
            "success": False,
            "message": "Doctor profile not found",
        }), 404

    # --------------------------------------------------------
    # Parse appointment date
    # --------------------------------------------------------

    try:
        appointment_datetime = datetime.fromisoformat(
            appointment_date.replace(
                "Z",
                "+00:00"
            )
        )

    except ValueError:
        return jsonify({
            "success": False,
            "message": (
                "Invalid appointment date format. "
                "Use ISO format such as "
                "2026-10-25T10:30:00"
            ),
        }), 400

    if appointment_datetime.tzinfo is None:
        appointment_datetime = appointment_datetime.replace(
            tzinfo=timezone.utc
        )

    # --------------------------------------------------------
    # Check doctor availability
    # --------------------------------------------------------

    existing_doctor_appointment = (
        appointments_collection.find_one(
            {
                "doctor_id": doctor_id,
                "appointment_date": appointment_datetime,
                "status": {
                    "$in": [
                        "pending",
                        "confirmed"
                    ]
                },
            }
        )
    )

    if existing_doctor_appointment:
        return jsonify({
            "success": False,
            "message": (
                "Doctor already has an appointment "
                "at this time"
            ),
        }), 409

    # --------------------------------------------------------
    # Create appointment
    # --------------------------------------------------------

    appointment = {
        "patient_id": patient_id,
        "doctor_id": doctor_id,
        "appointment_date": appointment_datetime,
        "reason": reason,
        "status": "pending",
        "created_at": datetime.now(timezone.utc),
    }

    result = appointments_collection.insert_one(
        appointment
    )

    return jsonify({
        "success": True,
        "message": "Appointment created successfully",
        "appointment": {
            "id": str(result.inserted_id),
            "patient_id": patient_id,
            "patient_name": patient.get(
                "name",
                ""
            ),
            "doctor_id": doctor_id,
            "doctor_name": doctor.get(
                "name",
                ""
            ),
            "appointment_date": (
                appointment_datetime.isoformat()
            ),
            "reason": reason,
            "status": "pending",
        },
    }), 201


# ============================================================
# GET ALL APPOINTMENTS
# ============================================================

@receptionist_bp.get("/appointments")
@token_required
@role_required("receptionist")
def get_all_appointments():

    appointments = appointments_collection.find(
        {}
    ).sort(
        "appointment_date",
        1
    )

    appointment_list = []

    for appointment in appointments:

        patient_id = appointment.get(
            "patient_id",
            ""
        )

        doctor_id = appointment.get(
            "doctor_id",
            ""
        )

        # ----------------------------------------------------
        # Find patient safely
        # ----------------------------------------------------

        patient = None

        try:
            patient = users_collection.find_one(
                {
                    "_id": ObjectId(patient_id),
                    "role": "patient",
                },
                {
                    "password_hash": 0
                }
            )

        except Exception:
            patient = None

        # ----------------------------------------------------
        # Find doctor safely
        # ----------------------------------------------------

        doctor = None

        try:
            doctor = users_collection.find_one(
                {
                    "_id": ObjectId(doctor_id),
                    "role": "doctor",
                },
                {
                    "password_hash": 0
                }
            )

        except Exception:
            doctor = None

        appointment_date = appointment.get(
            "appointment_date"
        )

        if appointment_date:
            appointment_date = appointment_date.isoformat()

        appointment_list.append({
            "id": str(appointment["_id"]),
            "patient_id": patient_id,
            "patient_name": (
                patient.get("name", "")
                if patient
                else ""
            ),
            "doctor_id": doctor_id,
            "doctor_name": (
                doctor.get("name", "")
                if doctor
                else ""
            ),
            "appointment_date": appointment_date,
            "reason": appointment.get(
                "reason",
                ""
            ),
            "status": appointment.get(
                "status",
                "pending"
            ),
        })

    return jsonify({
        "success": True,
        "appointments": appointment_list,
        "count": len(appointment_list),
    }), 200


# ============================================================
# CANCEL APPOINTMENT
# ============================================================

@receptionist_bp.patch(
    "/appointments/<appointment_id>/status"
)
@token_required
@role_required("receptionist")
def update_appointment_status(appointment_id):

    # --------------------------------------------------------
    # Validate appointment ID
    # --------------------------------------------------------

    try:
        appointment_object_id = ObjectId(
            appointment_id
        )

    except Exception:
        return jsonify({
            "success": False,
            "message": "Invalid appointment ID",
        }), 400

    # --------------------------------------------------------
    # Read request body
    # --------------------------------------------------------

    data = request.get_json(silent=True) or {}

    new_status = data.get(
        "status",
        ""
    ).strip().lower()

    # --------------------------------------------------------
    # Receptionist can only cancel
    # --------------------------------------------------------

    if new_status != "cancelled":
        return jsonify({
            "success": False,
            "message": (
                "Receptionist can only change "
                "appointment status to cancelled"
            ),
        }), 400

    # --------------------------------------------------------
    # Find appointment
    # --------------------------------------------------------

    appointment = appointments_collection.find_one({
        "_id": appointment_object_id
    })

    if not appointment:
        return jsonify({
            "success": False,
            "message": "Appointment not found",
        }), 404

    current_status = appointment.get(
        "status",
        "pending"
    )

    # --------------------------------------------------------
    # Only pending/confirmed appointments can be cancelled
    # --------------------------------------------------------

    if current_status in {
        "completed",
        "rejected",
        "cancelled"
    }:
        return jsonify({
            "success": False,
            "message": (
                f"Cannot cancel appointment "
                f"with status {current_status}"
            ),
        }), 400

    # --------------------------------------------------------
    # Cancel appointment
    # --------------------------------------------------------

    appointments_collection.update_one(
        {
            "_id": appointment_object_id
        },
        {
            "$set": {
                "status": "cancelled",
                "updated_at": datetime.now(
                    timezone.utc
                ),
            }
        }
    )

    return jsonify({
        "success": True,
        "message": "Appointment cancelled successfully",
        "appointment": {
            "id": appointment_id,
            "patient_id": appointment.get(
                "patient_id",
                ""
            ),
            "doctor_id": appointment.get(
                "doctor_id",
                ""
            ),
            "appointment_date": (
                appointment["appointment_date"].isoformat()
                if appointment.get("appointment_date")
                else None
            ),
            "reason": appointment.get(
                "reason",
                ""
            ),
            "status": "cancelled",
        },
    }), 200