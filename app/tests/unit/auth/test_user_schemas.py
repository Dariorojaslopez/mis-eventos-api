import pytest
from pydantic import ValidationError

pytestmark = pytest.mark.unit

from app.schemas.user import UserCreate
from app.tests.constants import INVALID_PASSWORD, VALID_PASSWORD


def test_user_create_valid() -> None:
    user = UserCreate(
        email="test@example.com",
        full_name="Test User",
        password=VALID_PASSWORD,
    )
    assert user.email == "test@example.com"


def test_user_create_weak_password() -> None:
    with pytest.raises(ValidationError):
        UserCreate(
            email="test@example.com",
            full_name="Test User",
            password=INVALID_PASSWORD,
        )
