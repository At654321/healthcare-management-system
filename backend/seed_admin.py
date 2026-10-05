from getpass import getpass

from pymongo.errors import DuplicateKeyError

from app.database import db
from app.utils.auth import hash_password


users_collection = db.get_collection("users")


def create_admin():
    print("\n=== Healthcare Management System ===")
    print("Create Admin Account\n")

    name = input("Admin name: ").strip()
    email = input("Admin email: ").strip().lower()
    password = getpass("Admin password: ")
    confirm_password = getpass("Confirm password: ")

    if not name or not email or not password:
        print("\nError: Name, email and password are required.")
        return

    if len(password) < 6:
        print("\nError: Password must be at least 6 characters long.")
        return

    if password != confirm_password:
        print("\nError: Passwords do not match.")
        return

    existing_user = users_collection.find_one(
        {"email": email}
    )

    if existing_user:
        print("\nError: This email is already registered.")
        return

    admin = {
        "name": name,
        "email": email,
        "password_hash": hash_password(password),
        "role": "admin",
    }

    try:
        result = users_collection.insert_one(admin)

    except DuplicateKeyError:
        print("\nError: This email is already registered.")
        return

    print("\nAdmin account created successfully!")
    print(f"Admin ID: {result.inserted_id}")
    print(f"Name: {name}")
    print(f"Email: {email}")
    print("Role: admin")


if __name__ == "__main__":
    create_admin()