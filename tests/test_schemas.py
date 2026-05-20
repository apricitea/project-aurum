"""Tests for request/response schema validation."""
import pytest
from pydantic import ValidationError
from src.api.schemas import LoginRequest, CreateAlertRequest


def test_login_request_password_min_length_is_12():
    """LoginRequest must reject passwords shorter than 12 characters."""
    with pytest.raises(ValidationError):
        LoginRequest(username="testuser", password="short")


def test_login_request_password_exactly_12_accepted():
    req = LoginRequest(username="testuser", password="Ab#defgh1234")
    assert req.password == "Ab#defgh1234"


def test_login_request_password_11_chars_rejected():
    with pytest.raises(ValidationError):
        LoginRequest(username="testuser", password="Ab#defgh123")


def test_create_alert_request_valid():
    req = CreateAlertRequest(
        alert_type="risk_breach",
        message="Portfolio exceeded limit",
        priority="high",
    )
    assert req.priority == "high"


def test_create_alert_request_message_too_long():
    with pytest.raises(ValidationError):
        CreateAlertRequest(
            alert_type="x",
            message="x" * 1001,
        )
