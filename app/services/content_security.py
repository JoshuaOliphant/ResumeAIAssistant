from fastapi import HTTPException, status
import re

MAX_CONTENT_LENGTH = 10000


def sanitize_text(text: str, max_length: int = MAX_CONTENT_LENGTH) -> str:
    """Sanitize text by stripping scripts and trimming length."""
    sanitized = re.sub(r"<script.*?>.*?</script>", "", text, flags=re.IGNORECASE | re.DOTALL)
    sanitized = sanitized.replace("\x00", "")
    if len(sanitized) > max_length:
        sanitized = sanitized[:max_length]
    return sanitized


def validate_content_size(text: str, max_length: int = MAX_CONTENT_LENGTH) -> None:
    """Validate text length."""
    if len(text) > max_length:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"Content too large (max {max_length} characters)",
        )


def detect_malicious_content(text: str) -> None:
    """Detect simple malicious patterns."""
    if re.search(r"<script", text, re.IGNORECASE):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Malicious content detected",
        )
