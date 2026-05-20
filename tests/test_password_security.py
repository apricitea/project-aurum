"""Tests for password validation policy."""
import sys


def _load_password_security():
    import importlib
    # Clear the module if it was cached with a mock config dependency
    mod_name = "src.api.password_security"
    if mod_name in sys.modules:
        return sys.modules[mod_name]
    return importlib.import_module(mod_name)


def test_valid_password_passes():
    m = _load_password_security()
    result = m.validate_password("MySecureP@ss12!")
    assert result["is_valid"] is True
    assert result["errors"] == []


def test_short_password_fails():
    m = _load_password_security()
    result = m.validate_password("Short1!")
    assert result["is_valid"] is False
    assert any("12" in e for e in result["errors"])


def test_no_uppercase_fails():
    m = _load_password_security()
    result = m.validate_password("mysecurep@ss12!")
    assert result["is_valid"] is False
    assert any("uppercase" in e.lower() for e in result["errors"])


def test_no_lowercase_fails():
    m = _load_password_security()
    result = m.validate_password("MYSECUREP@SS12!")
    assert result["is_valid"] is False
    assert any("lowercase" in e.lower() for e in result["errors"])


def test_no_digit_fails():
    m = _load_password_security()
    result = m.validate_password("MySecureP@ssWord!")
    assert result["is_valid"] is False
    assert any("digit" in e.lower() for e in result["errors"])


def test_insufficient_special_chars_fails():
    m = _load_password_security()
    result = m.validate_password("MySecurePassword1")
    assert result["is_valid"] is False
    assert any("special" in e.lower() for e in result["errors"])


def test_exactly_two_special_chars_passes():
    m = _load_password_security()
    result = m.validate_password("MySecurePass12@!")
    assert result["is_valid"] is True


def test_generate_secure_password_meets_policy():
    m = _load_password_security()
    for _ in range(10):
        pw = m.generate_secure_password(16)
        result = m.validate_password(pw)
        assert result["is_valid"] is True, (
            f"Generated password failed policy: '{pw}' — {result['errors']}"
        )


def test_hash_and_verify_round_trip():
    m = _load_password_security()
    pw = "TestPass@word12"
    h = m.hash_password(pw)
    assert m.verify_password(pw, h)
    assert not m.verify_password("wrong", h)


def test_verify_password_wrong_returns_false():
    m = _load_password_security()
    h = m.hash_password("CorrectP@ss12")
    assert not m.verify_password("WrongP@ss12", h)
