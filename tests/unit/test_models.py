from datetime import datetime, timezone, timedelta

from app.modules.auth.models import build_user_document
from app.modules.products.models import build_product_document
from app.modules.inventory.models import build_inventory_document, build_scheduled_notifications
from bson import ObjectId


class TestBuildUserDocument:
    def test_required_fields_present(self):
        doc = build_user_document("John", "john@example.com", "hashed_pw")
        assert doc["name"] == "John"
        assert doc["email"] == "john@example.com"
        assert doc["hashed_password"] == "hashed_pw"

    def test_defaults(self):
        doc = build_user_document("John", "john@example.com", "hashed_pw")
        assert doc["is_active"] is True
        assert doc["fcm_token"] is None
        assert doc["notification_days_before"] == [3, 1, 0.5]

    def test_created_at_is_utc(self):
        doc = build_user_document("John", "john@example.com", "hashed_pw")
        assert doc["created_at"].tzinfo == timezone.utc


class TestBuildProductDocument:
    def test_off_source_is_verified(self):
        doc = build_product_document(name="Milk", source="off")
        assert doc["is_verified"] is True

    def test_manual_source_not_verified(self):
        doc = build_product_document(name="Milk", source="manual")
        assert doc["is_verified"] is False

    def test_optional_fields_default_none(self):
        doc = build_product_document(name="Milk", source="manual")
        assert doc["barcode"] is None
        assert doc["brand"] is None
        assert doc["image_url"] is None
        assert doc["quantity"] is None

    def test_tags_default_empty_list(self):
        doc = build_product_document(name="Milk", source="manual")
        assert doc["tags"] == []

    def test_all_fields(self):
        doc = build_product_document(
            name="Milk",
            source="off",
            barcode="123456",
            brand="DairyFarm",
            tags=["dairy", "milk"],
            image_url="http://example.com/img.jpg",
            quantity="1 l",
        )
        assert doc["barcode"] == "123456"
        assert doc["brand"] == "DairyFarm"
        assert doc["tags"] == ["dairy", "milk"]


class TestBuildScheduledNotifications:
    def test_returns_list(self):
        exp = datetime.now(timezone.utc) + timedelta(days=5)
        result = build_scheduled_notifications(exp, [3, 1, 0.5])
        assert isinstance(result, list)

    def test_correct_count(self):
        exp = datetime.now(timezone.utc) + timedelta(days=5)
        result = build_scheduled_notifications(exp, [3, 1, 0.5])
        assert len(result) == 3

    def test_past_thresholds_skipped(self):
        """If send_at is in the past — notification is not planned"""
        exp = datetime.now(timezone.utc) + timedelta(days=2)
        result = build_scheduled_notifications(exp, [3, 1, 0.5])
        # threshold=3 gives send_at in the past, needs to be skipped
        assert len(result) == 2

    def test_sent_is_false(self):
        exp = datetime.now(timezone.utc) + timedelta(days=5)
        result = build_scheduled_notifications(exp, [3, 1, 0.5])
        assert all(n["sent"] is False for n in result)

    def test_notification_fields(self):
        exp = datetime.now(timezone.utc) + timedelta(days=5)
        result = build_scheduled_notifications(exp, [3])
        assert "threshold" in result[0]
        assert "send_at" in result[0]
        assert "sent" in result[0]


class TestBuildInventoryDocument:
    def test_required_fields(self):
        user_id = ObjectId()
        exp = datetime.now(timezone.utc) + timedelta(days=5)
        doc = build_inventory_document(
            user_id=user_id,
            expiration_date=exp,
            amount=1.0,
            unit="l",
            scheduled_notifications=[],
        )
        assert doc["user_id"] == user_id
        assert doc["amount"] == 1.0
        assert doc["unit"] == "l"
        assert doc["status"] == "active"

    def test_optional_fields_default_none(self):
        doc = build_inventory_document(
            user_id=ObjectId(),
            expiration_date=datetime.now(timezone.utc) + timedelta(days=5),
            amount=1.0,
            unit="l",
            scheduled_notifications=[],
        )
        assert doc["product_id"] is None
        assert doc["barcode"] is None
        assert doc["custom_name"] is None
        assert doc["notes"] is None
        assert doc["location"] is None

    def test_timestamps_are_utc(self):
        doc = build_inventory_document(
            user_id=ObjectId(),
            expiration_date=datetime.now(timezone.utc) + timedelta(days=5),
            amount=1.0,
            unit="l",
            scheduled_notifications=[],
        )
        assert doc["added_at"].tzinfo == timezone.utc
        assert doc["updated_at"].tzinfo == timezone.utc