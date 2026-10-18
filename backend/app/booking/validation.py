"""Validation boundaries for booking inputs matching TECHNICAL_DESIGN.md §12.3."""

import re
from typing import Optional, Tuple

# Regex to check that name contains only letters, spaces, hyphens, apostrophes, and dots
NAME_ALLOWED_PATTERN = re.compile(r"^[\w\s'\-\.]+$", re.UNICODE)
# Reject obvious SQL or HTML injection keywords
INJECTION_PATTERN = re.compile(r"(<[^>]*>|--|;|\b(drop|select|insert|delete|table|union|exec)\b)", re.IGNORECASE)

EMAIL_STRICT_PATTERN = re.compile(
    r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+(?:\.[a-zA-Z0-9-]+)+$"
)


def validate_full_name(name: Optional[str]) -> Tuple[bool, Optional[str]]:
    """Validate full name input (TECHNICAL_DESIGN §12.3).
    
    Rules:
    - Trimmed string with length between 2 and 80 characters.
    - At least two tokens (first and last name).
    - Contains Unicode letters, spaces, hyphens, apostrophes, or dots.
    - No script, HTML tags, or SQL injection keywords.
    
    Returns:
        (is_valid, cleaned_name_or_reason)
    """
    if not name or not isinstance(name, str):
        return False, "Full name must be provided."

    trimmed = " ".join(name.strip().split())
    if len(trimmed) < 2:
        return False, "Full name must be at least 2 characters."
    if len(trimmed) > 80:
        return False, "Full name cannot exceed 80 characters."

    if INJECTION_PATTERN.search(trimmed):
        return False, "Full name contains invalid or disallowed characters."

    if not NAME_ALLOWED_PATTERN.match(trimmed):
        return False, "Full name may only contain letters, spaces, hyphens, apostrophes, and dots."

    tokens = trimmed.split()
    if len(tokens) < 2:
        return False, "Please provide both your first and last name."

    # Verify each token has at least one letter and does not consist purely of punctuation
    for token in tokens:
        letters_only = re.sub(r"[^a-zA-Z\u00C0-\u024F\u1E00-\u1EFF]", "", token)
        if not letters_only:
            return False, "Each part of your name must contain letters."

    return True, trimmed


def validate_email(email: Optional[str]) -> Tuple[bool, Optional[str]]:
    """Validate email address input (TECHNICAL_DESIGN §12.3).
    
    Rules:
    - Trimmed string with length <= 254 characters.
    - Exactly one '@', non-empty local part, and a domain containing at least one dot.
    - No whitespace.
    - Normalised to lowercase.
    
    Returns:
        (is_valid, cleaned_email_or_reason)
    """
    if not email or not isinstance(email, str):
        return False, "Email address must be provided."

    trimmed = email.strip()
    if len(trimmed) > 254:
        return False, "Email address cannot exceed 254 characters."

    if " " in trimmed or "\t" in trimmed or "\n" in trimmed:
        return False, "Email address cannot contain whitespace."

    if not EMAIL_STRICT_PATTERN.match(trimmed):
        return False, "Please provide a valid email address (e.g. name@example.com)."

    normalized = trimmed.lower()
    return True, normalized
