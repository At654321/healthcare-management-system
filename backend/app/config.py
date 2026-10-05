import os

from dotenv import load_dotenv


load_dotenv()


class Config:
    MONGO_URI = os.getenv("MONGO_URI")
    MONGO_DB_NAME = os.getenv("MONGO_DB_NAME", "healthcare_db")
    JWT_SECRET = os.getenv("JWT_SECRET")

    if not MONGO_URI:
        raise ValueError("MONGO_URI is not set in .env")

    if not JWT_SECRET:
        raise ValueError("JWT_SECRET is not set in .env")