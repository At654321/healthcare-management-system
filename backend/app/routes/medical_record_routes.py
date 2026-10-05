from datetime import datetime, timezone
from io import BytesIO

from bson import ObjectId
from flask import Blueprint, jsonify, request, send_file
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas

from app.database import db
from app.utils.auth import role_required, token_required


medical_record_bp = Blueprint(
    "medical_record",
    __name__,
    url_prefix="/api/medical-records",
)

medical_records_collection = db["medical_records"]
appointments_collection = db["appointments"]
users_collection = db["users"]
doctors_collection = db["doctors"]


@medical_record_bp.post("")
@token_required
@role_required("doctor")
def create_medical_record():
    doctor_user_id = request.user.get("user_id")

    data = request.get_json(silent=True) or {}

    appointment_id = data.get("appointment_id", "").strip()
    diagnosis = data.get("diagnosis", "").strip()
    medicines = data.get("medicines", [])
    instructions = data.get("instructions", "").strip()

    if not appointment_id or not diagnosis:
        return jsonify(
            {
                "success": False,
                "message": "Appointment ID and diagnosis are required",
            }
        ), 400

    if not isinstance(medicines, list):
        return jsonify(
            {
                "success": False,
                "message": "Medicines must be a list",
            }
        ), 400

    try:
        appointment_object_id = ObjectId(appointment_id)

    except Exception:
        return jsonify(
            {
                "success": False,
                "message": "Invalid appointment ID",
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
                "message": (
                    "Appointment not found or does not belong "
                    "to this doctor"
                ),
            }
        ), 404

    if appointment.get("status") != "completed":
        return jsonify(
            {
                "success": False,
                "message": (
                    "Medical record can only be created "
                    "for a completed appointment"
                ),
            }
        ), 400

    existing_record = medical_records_collection.find_one(
        {
            "appointment_id": appointment_id,
        }
    )

    if existing_record:
        return jsonify(
            {
                "success": False,
                "message": (
                    "Medical record already exists "
                    "for this appointment"
                ),
            }
        ), 409

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

    doctor_profile = doctors_collection.find_one(
        {
            "user_id": doctor_user_id,
        }
    )

    medical_record = {
        "appointment_id": appointment_id,
        "patient_id": appointment["patient_id"],
        "doctor_id": doctor_user_id,
        "diagnosis": diagnosis,
        "medicines": medicines,
        "instructions": instructions,
        "created_at": datetime.now(timezone.utc),
    }

    result = medical_records_collection.insert_one(
        medical_record
    )

    return jsonify(
        {
            "success": True,
            "message": "Medical record created successfully",
            "medical_record": {
                "id": str(result.inserted_id),
                "appointment_id": appointment_id,
                "patient_id": appointment["patient_id"],
                "doctor_id": doctor_user_id,
                "doctor_name": (
                    doctor_user.get("name", "")
                    if doctor_user
                    else ""
                ),
                "specialization": (
                    doctor_profile.get(
                        "specialization",
                        "",
                    )
                    if doctor_profile
                    else ""
                ),
                "hospital": (
                    doctor_profile.get(
                        "hospital",
                        "",
                    )
                    if doctor_profile
                    else ""
                ),
                "diagnosis": diagnosis,
                "medicines": medicines,
                "instructions": instructions,
                "created_at": medical_record[
                    "created_at"
                ].isoformat(),
            },
        }
    ), 201


@medical_record_bp.get("/patient")
@token_required
@role_required("patient")
def get_patient_medical_records():
    patient_user_id = request.user.get("user_id")

    records = medical_records_collection.find(
        {
            "patient_id": patient_user_id,
        }
    ).sort(
        "created_at",
        -1,
    )

    record_list = []

    for record in records:
        record_list.append(
            {
                "id": str(record["_id"]),
                "appointment_id": record["appointment_id"],
                "patient_id": record["patient_id"],
                "doctor_id": record["doctor_id"],
                "diagnosis": record["diagnosis"],
                "medicines": record.get(
                    "medicines",
                    [],
                ),
                "instructions": record.get(
                    "instructions",
                    "",
                ),
                "created_at": record[
                    "created_at"
                ].isoformat(),
            }
        )

    return jsonify(
        {
            "success": True,
            "medical_records": record_list,
            "count": len(record_list),
        }
    ), 200


@medical_record_bp.get("/doctor/patient/<patient_user_id>")
@token_required
@role_required("doctor")
def get_patient_medical_history_for_doctor(
    patient_user_id,
):
    doctor_user_id = request.user.get("user_id")

    try:
        patient_object_id = ObjectId(patient_user_id)

    except Exception:
        return jsonify(
            {
                "success": False,
                "message": "Invalid patient ID",
            }
        ), 400

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

    doctor_has_appointment = appointments_collection.find_one(
        {
            "doctor_id": doctor_user_id,
            "patient_id": patient_user_id,
        }
    )

    if not doctor_has_appointment:
        return jsonify(
            {
                "success": False,
                "message": (
                    "You do not have an appointment "
                    "with this patient"
                ),
            }
        ), 403

    records = medical_records_collection.find(
        {
            "patient_id": patient_user_id,
        }
    ).sort(
        "created_at",
        -1,
    )

    record_list = []

    for record in records:
        record_list.append(
            {
                "id": str(record["_id"]),
                "appointment_id": record[
                    "appointment_id"
                ],
                "patient_id": record["patient_id"],
                "doctor_id": record["doctor_id"],
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
                "created_at": record[
                    "created_at"
                ].isoformat(),
            }
        )

    return jsonify(
        {
            "success": True,
            "patient": {
                "id": str(patient_user["_id"]),
                "name": patient_user.get(
                    "name",
                    "",
                ),
                "email": patient_user.get(
                    "email",
                    "",
                ),
            },
            "medical_records": record_list,
            "count": len(record_list),
        }
    ), 200


def generate_prescription_pdf(record):
    """Generate a prescription PDF from stored medical record data."""

    buffer = BytesIO()

    pdf = canvas.Canvas(
        buffer,
        pagesize=A4,
    )

    width, height = A4

    left_margin = 20 * mm
    right_margin = 20 * mm

    y = height - 25 * mm

    pdf.setTitle("Medical Prescription")

    pdf.setFont(
        "Helvetica-Bold",
        18,
    )

    pdf.drawCentredString(
        width / 2,
        y,
        "HEALTHCARE MANAGEMENT SYSTEM",
    )

    y -= 10 * mm

    pdf.setFont(
        "Helvetica-Bold",
        14,
    )

    pdf.drawCentredString(
        width / 2,
        y,
        "MEDICAL PRESCRIPTION",
    )

    y -= 12 * mm

    pdf.line(
        left_margin,
        y,
        width - right_margin,
        y,
    )

    y -= 10 * mm

    doctor_user_id = record.get(
        "doctor_id",
        "",
    )

    patient_user_id = record.get(
        "patient_id",
        "",
    )

    doctor_name = "Doctor"
    doctor_profile = None

    try:
        doctor_user = users_collection.find_one(
            {
                "_id": ObjectId(doctor_user_id),
                "role": "doctor",
            }
        )

        doctor_profile = doctors_collection.find_one(
            {
                "user_id": doctor_user_id,
            }
        )

        if doctor_user:
            doctor_name = doctor_user.get(
                "name",
                "Doctor",
            )

    except Exception:
        pass

    patient_name = "Patient"

    try:
        patient_user = users_collection.find_one(
            {
                "_id": ObjectId(patient_user_id),
                "role": "patient",
            }
        )

        if patient_user:
            patient_name = patient_user.get(
                "name",
                "Patient",
            )

    except Exception:
        pass

    specialization = ""
    hospital = ""

    if doctor_profile:
        specialization = doctor_profile.get(
            "specialization",
            "",
        )

        hospital = doctor_profile.get(
            "hospital",
            "",
        )

    pdf.setFont(
        "Helvetica-Bold",
        11,
    )

    pdf.drawString(
        left_margin,
        y,
        "Patient:",
    )

    pdf.setFont(
        "Helvetica",
        11,
    )

    pdf.drawString(
        left_margin + 30 * mm,
        y,
        patient_name,
    )

    y -= 7 * mm

    pdf.setFont(
        "Helvetica-Bold",
        11,
    )

    pdf.drawString(
        left_margin,
        y,
        "Doctor:",
    )

    pdf.setFont(
        "Helvetica",
        11,
    )

    pdf.drawString(
        left_margin + 30 * mm,
        y,
        doctor_name,
    )

    y -= 7 * mm

    if specialization:
        pdf.setFont(
            "Helvetica-Bold",
            11,
        )

        pdf.drawString(
            left_margin,
            y,
            "Specialization:",
        )

        pdf.setFont(
            "Helvetica",
            11,
        )

        pdf.drawString(
            left_margin + 40 * mm,
            y,
            specialization,
        )

        y -= 7 * mm

    if hospital:
        pdf.setFont(
            "Helvetica-Bold",
            11,
        )

        pdf.drawString(
            left_margin,
            y,
            "Hospital:",
        )

        pdf.setFont(
            "Helvetica",
            11,
        )

        pdf.drawString(
            left_margin + 30 * mm,
            y,
            hospital,
        )

        y -= 7 * mm

    y -= 5 * mm

    pdf.line(
        left_margin,
        y,
        width - right_margin,
        y,
    )

    y -= 10 * mm

    pdf.setFont(
        "Helvetica-Bold",
        12,
    )

    pdf.drawString(
        left_margin,
        y,
        "Diagnosis",
    )

    y -= 7 * mm

    pdf.setFont(
        "Helvetica",
        11,
    )

    diagnosis = record.get(
        "diagnosis",
        "",
    )

    pdf.drawString(
        left_margin,
        y,
        diagnosis,
    )

    y -= 12 * mm

    pdf.setFont(
        "Helvetica-Bold",
        12,
    )

    pdf.drawString(
        left_margin,
        y,
        "Medicines",
    )

    y -= 8 * mm

    medicines = record.get(
        "medicines",
        [],
    )

    if medicines:
        for index, medicine in enumerate(
            medicines,
            start=1,
        ):
            if y < 35 * mm:
                pdf.showPage()
                y = height - 25 * mm

            medicine_name = medicine.get(
                "name",
                "",
            )

            dosage = medicine.get(
                "dosage",
                "",
            )

            frequency = medicine.get(
                "frequency",
                "",
            )

            duration = medicine.get(
                "duration",
                "",
            )

            medicine_text = (
                f"{index}. {medicine_name}"
            )

            pdf.setFont(
                "Helvetica-Bold",
                10,
            )

            pdf.drawString(
                left_margin,
                y,
                medicine_text,
            )

            y -= 5 * mm

            pdf.setFont(
                "Helvetica",
                10,
            )

            if dosage:
                pdf.drawString(
                    left_margin + 8 * mm,
                    y,
                    f"Dosage: {dosage}",
                )

                y -= 5 * mm

            if frequency:
                pdf.drawString(
                    left_margin + 8 * mm,
                    y,
                    f"Frequency: {frequency}",
                )

                y -= 5 * mm

            if duration:
                pdf.drawString(
                    left_margin + 8 * mm,
                    y,
                    f"Duration: {duration}",
                )

                y -= 8 * mm

    else:
        pdf.setFont(
            "Helvetica",
            10,
        )

        pdf.drawString(
            left_margin,
            y,
            "No medicines prescribed.",
        )

        y -= 8 * mm

    pdf.setFont(
        "Helvetica-Bold",
        12,
    )

    pdf.drawString(
        left_margin,
        y,
        "Instructions",
    )

    y -= 7 * mm

    pdf.setFont(
        "Helvetica",
        10,
    )

    instructions = record.get(
        "instructions",
        "",
    )

    if instructions:
        pdf.drawString(
            left_margin,
            y,
            instructions,
        )
    else:
        pdf.drawString(
            left_margin,
            y,
            "No additional instructions.",
        )

    y -= 20 * mm

    pdf.line(
        width - 75 * mm,
        y,
        width - right_margin,
        y,
    )

    y -= 6 * mm

    pdf.setFont(
        "Helvetica",
        9,
    )

    pdf.drawRightString(
        width - right_margin,
        y,
        f"Doctor: {doctor_name}",
    )

    y -= 6 * mm

    pdf.drawRightString(
        width - right_margin,
        y,
        "Authorized Medical Record",
    )

    pdf.showPage()
    pdf.save()

    buffer.seek(0)

    return buffer


@medical_record_bp.get("/<record_id>/pdf")
@token_required
def download_medical_record_pdf(record_id):
    user_id = request.user.get("user_id")
    user_role = request.user.get("role")

    try:
        record_object_id = ObjectId(record_id)

    except Exception:
        return jsonify(
            {
                "success": False,
                "message": "Invalid medical record ID",
            }
        ), 400

    record = medical_records_collection.find_one(
        {
            "_id": record_object_id,
        }
    )

    if not record:
        return jsonify(
            {
                "success": False,
                "message": "Medical record not found",
            }
        ), 404

    if user_role == "patient":
        if record.get("patient_id") != user_id:
            return jsonify(
                {
                    "success": False,
                    "message": (
                        "You do not have permission "
                        "to access this prescription"
                    ),
                }
            ), 403

    elif user_role == "doctor":
        if record.get("doctor_id") != user_id:
            return jsonify(
                {
                    "success": False,
                    "message": (
                        "You do not have permission "
                        "to access this prescription"
                    ),
                }
            ), 403

    else:
        return jsonify(
            {
                "success": False,
                "message": (
                    "You do not have permission "
                    "to access this prescription"
                ),
            }
        ), 403

    pdf_buffer = generate_prescription_pdf(
        record
    )

    filename = (
        f"prescription_{record_id}.pdf"
    )

    return send_file(
        pdf_buffer,
        mimetype="application/pdf",
        as_attachment=True,
        download_name=filename,
    )