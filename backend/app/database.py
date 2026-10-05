from pymongo import MongoClient

from app.config import Config


client = MongoClient(
    Config.MONGO_URI,
    serverSelectionTimeoutMS=10000,
)

db = client[Config.MONGO_DB_NAME]


def check_database_connection():
    """Check whether MongoDB is reachable."""
    client.admin.command("ping")
    return True