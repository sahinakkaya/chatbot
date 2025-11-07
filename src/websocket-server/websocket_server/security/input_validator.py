"""
Input validation and sanitization to prevent security vulnerabilities.

Protects against:
- Prompt injection attacks
- XSS attacks
- Control character injection
- Malicious input patterns
"""

import html
import logging
import re
from typing import Optional

logger = logging.getLogger(__name__)


class InputValidationError(Exception):
    """Raised when input validation fails"""

    pass


class InputValidator:
    """Validates and sanitizes user input"""

    # Patterns that might indicate prompt injection attempts
    SUSPICIOUS_PATTERNS = [
        r"ignore\s+(previous|above|all)\s+(instructions?|prompts?|rules?)",
        r"you\s+are\s+now",
        r"new\s+instructions?",
        r"system\s*:",
        r"<\s*system\s*>",
        r"disregard\s+(previous|above|all)",
        r"forget\s+(everything|all|previous)",
        r"roleplay\s+as",
        r"pretend\s+(you|to)\s+(are|be)",
    ]

    # Compile patterns for efficiency
    COMPILED_PATTERNS = [
        re.compile(pattern, re.IGNORECASE) for pattern in SUSPICIOUS_PATTERNS
    ]

    @staticmethod
    def sanitize_content(content: str) -> str:
        """
        Sanitize message content to prevent injection attacks.

        - Removes control characters
        - Escapes HTML entities
        - Normalizes whitespace
        """
        if not content:
            return ""

        # Remove control characters (except newline, tab)
        content = "".join(
            char for char in content if char.isprintable() or char in ["\n", "\t"]
        )

        # Normalize whitespace (collapse multiple spaces/newlines)
        content = re.sub(r"\s+", " ", content)
        content = content.strip()

        # Escape HTML to prevent XSS
        content = html.escape(content)

        return content

    @classmethod
    def check_suspicious_patterns(cls, content: str) -> Optional[str]:
        """
        Check for suspicious patterns that might indicate prompt injection.

        Returns None if clean, or a warning message if suspicious.
        """
        content_lower = content.lower()

        for pattern in cls.COMPILED_PATTERNS:
            if pattern.search(content_lower):
                matched_pattern = pattern.pattern
                logger.warning(
                    f"Suspicious pattern detected: {matched_pattern} in content: {content[:100]}"
                )
                return f"Your message contains potentially problematic content. Please rephrase."

        return None

    @classmethod
    def validate_and_sanitize(cls, content: str, max_length: int = 500) -> str:
        """
        Main validation and sanitization function.

        Returns sanitized content if valid.
        Raises InputValidationError if validation fails.
        """
        if not content or not content.strip():
            raise InputValidationError("Message content cannot be empty")

        # Check length before sanitization
        if len(content) > max_length:
            raise InputValidationError(
                f"Message too long. Maximum {max_length} characters allowed."
            )

        # Sanitize content
        sanitized = cls.sanitize_content(content)

        if not sanitized:
            raise InputValidationError("Message content is invalid after sanitization")

        # Check for suspicious patterns
        suspicious_warning = cls.check_suspicious_patterns(sanitized)
        if suspicious_warning:
            raise InputValidationError(suspicious_warning)

        # Final length check after sanitization
        if len(sanitized) > max_length:
            raise InputValidationError(
                f"Message too long. Maximum {max_length} characters allowed."
            )

        return sanitized

    @staticmethod
    def sanitize_response(response: str) -> str:
        """
        Sanitize AI response before sending to client.

        Prevents potential XSS if AI generates malicious content.
        """
        if not response:
            return ""

        # Remove any potential script tags or HTML
        response = re.sub(r"<script[^>]*>.*?</script>", "", response, flags=re.DOTALL)
        response = re.sub(r"<[^>]+>", "", response)  # Remove all HTML tags

        return response.strip()
