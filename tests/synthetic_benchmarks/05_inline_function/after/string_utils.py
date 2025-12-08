"""String utility functions."""

def format_name(first: str, last: str) -> str:
    """Format full name with inlined capitalize."""
    first_formatted = first[0].upper() + first[1:].lower() if first else ""
    last_formatted = last[0].upper() + last[1:].lower() if last else ""
    return f"{first_formatted} {last_formatted}"

def format_email(name: str, domain: str) -> str:
    """Format email address with inlined capitalize."""
    name_formatted = name[0].upper() + name[1:].lower() if name else ""
    return f"{name_formatted}@{domain}"
