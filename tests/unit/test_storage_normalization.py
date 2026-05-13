from app.modules.storage.normalization import normalize_storage_name
from app.modules.storage.schemas import StorageRule


def test_normalize_storage_name_removes_quantity_and_noise():
    assert normalize_storage_name("Свежие яблоки 1 кг") == "яблоки"


def test_storage_rule_rejects_invalid_range():
    try:
        StorageRule.model_validate({
            "location": "fridge",
            "state": "whole",
            "recommended_days": 5,
            "min_days": 10,
            "max_days": 3,
        })
    except ValueError:
        return

    raise AssertionError("Invalid storage range was accepted")
