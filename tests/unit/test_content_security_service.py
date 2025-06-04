import pytest
from fastapi import HTTPException

from app.services import content_security


def test_sanitize_text_strips_script():
    text = "<script>alert('x')</script>hello"
    sanitized = content_security.sanitize_text(text)
    assert "script" not in sanitized.lower()


def test_detect_malicious_content_raises():
    with pytest.raises(HTTPException):
        content_security.detect_malicious_content("<script>alert(1)</script>")


def test_validate_content_size_raises():
    oversized = "a" * (content_security.MAX_CONTENT_LENGTH + 1)
    with pytest.raises(HTTPException):
        content_security.validate_content_size(oversized)
