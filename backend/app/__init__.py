from flask import Flask
from flask_cors import CORS

from app.config import Config
from app.routes.auth_routes import auth_bp
from app.routes.patient_routes import patient_bp
from app.routes.doctor_routes import doctor_bp
from app.routes.admin_routes import admin_bp
from app.routes.receptionist_routes import receptionist_bp
from app.routes.appointment_routes import appointment_bp
from app.routes.medical_record_routes import medical_record_bp


def create_app():
    app = Flask(__name__)

    app.config.from_object(Config)

    CORS(app)

    app.register_blueprint(auth_bp)
    app.register_blueprint(patient_bp)
    app.register_blueprint(doctor_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(receptionist_bp)
    app.register_blueprint(appointment_bp)
    app.register_blueprint(medical_record_bp)

    @app.get("/")
    def home():
        return {
            "success": True,
            "message": "Healthcare Management System API is running",
        }

    return app