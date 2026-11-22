from datetime import date
from decimal import Decimal, InvalidOperation
from urllib.parse import unquote, urlsplit


def text_field(form, name, limit, *, required=False):
    value = form.get(name, "").strip()
    label = name.replace("_", " ").capitalize()
    if required and not value:
        raise ValueError(f"{label} is required.")
    if len(value) > limit or "\x00" in value:
        raise ValueError(f"{label} must be valid text of at most {limit} characters.")
    return value or None


def date_field(form, name, *, required=False):
    value = text_field(form, name, 10, required=required)
    try:
        return date.fromisoformat(value) if value else None
    except ValueError:
        raise ValueError(f"Enter a valid {name.replace('_', ' ')}.") from None


def number_field(form, name, maximum, places):
    value = text_field(form, name, 32)
    if not value:
        return None
    try:
        number = Decimal(value)
        if number.is_finite() and 0 <= number <= Decimal(str(maximum)) and number == round(number, places):
            return number
    except (InvalidOperation, ValueError):
        pass
    raise ValueError(f"Enter a valid {name.replace('_', ' ')}.")


def local_redirect_target(value):
    if not value:
        return None
    decoded = unquote(value)
    if not decoded.startswith("/") or decoded.startswith("//") or "\\" in decoded:
        return None
    if any(ord(char) < 32 or ord(char) == 127 for char in decoded):
        return None
    return value if value.startswith("/") else None


def public_http_url(value):
    if not value or "\\" in value or any(char.isspace() for char in value):
        return None
    try:
        parsed = urlsplit(value)
        if parsed.scheme in {"http", "https"} and parsed.hostname and not parsed.username:
            return value
    except ValueError:
        pass
    return None
