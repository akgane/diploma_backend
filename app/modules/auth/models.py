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
        "fcm_token": None,
        "notification_days_before": [3, 1, 0.5],
        "created_at": datetime.now(timezone.utc),
    }