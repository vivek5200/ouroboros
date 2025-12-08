"""String utility functions."""

def format_name(first: str, last: str) -> str:
    """Format full name."""
    return f"{capitalize(first)} {capitalize(last)}"

def capitalize(text: str) -> str:
    """Capitalize first letter of string."""
    if not text:
        return ""
    return text[0].upper() + text[1:].lower()

def format_email(name: str, domain: str) -> str:
    """Format email address."""
    return f"{capitalize(name)}@{domain}"
