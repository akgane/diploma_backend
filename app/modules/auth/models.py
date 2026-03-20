from datetime import datetime, timezone


def build_user_document(name: str, email: str, hashed_password: str) -> dict:
    """
    Document for MongoDB paste
    _id generates automatically
    """

    return {
        "name": name,
        "email": email,
        "hashed_password": hashed_password,
        "is_active": True,
        "created_at": datetime.now(timezone.utc),
    }