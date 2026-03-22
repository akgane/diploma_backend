from unittest.mock import patch

from app.core.security import (
    hash_password,
    verify_password,
    create_access_token,
    decode_access_token,
)


# region Password

class TestHashPassword:
    def test_returns_string(self):
        result = hash_password("mypassword")
        assert isinstance(result, str)

    def test_not_equal_to_plain(self):
        result = hash_password("mypassword")
        assert result != "mypassword"

    def test_same_password_different_hashes(self):
        hash1 = hash_password("mypassword")
        hash2 = hash_password("mypassword")
        assert hash1 != hash2


class TestVerifyPassword:
    def test_correct_password(self):
        hashed = hash_password("mypassword")
        assert verify_password("mypassword", hashed) is True

    def test_wrong_password(self):
        hashed = hash_password("mypassword")
        assert verify_password("wrongpassword", hashed) is False

    def test_empty_password(self):
        hashed = hash_password("mypassword")
        assert verify_password("", hashed) is False


# endregion Password

# region JWT

class TestCreateAccessToken:
    def test_returns_string(self):
        token = create_access_token("user_id_123")
        assert isinstance(token, str)

    def test_token_not_empty(self):
        token = create_access_token("user_id_123")
        assert len(token) > 0

    def test_different_subjects_different_tokens(self):
        token1 = create_access_token("user_id_1")
        token2 = create_access_token("user_id_2")
        assert token1 != token2


class TestDecodeAccessToken:
    def test_valid_token(self):
        token = create_access_token("user_id_123")
        result = decode_access_token(token)
        assert result == "user_id_123"

    def test_invalid_token_returns_none(self):
        result = decode_access_token("this.is.invalid")
        assert result is None

    def test_empty_token_returns_none(self):
        result = decode_access_token("")
        assert result is None

    def test_expired_token_returns_none(self):
        with patch("app.core.security.timedelta") as mock_timedelta:
            from datetime import timedelta
            mock_timedelta.return_value = timedelta(minutes=-1)
            token = create_access_token("user_id_123")

        result = decode_access_token(token)
        assert result is None

# endregion JWT
