import re
from datetime import datetime

from app.utils.dt import now

_PHONE_CLEAN_RE = re.compile(r"[\s\-\(\)]")
_PHONE_DIGITS_RE = re.compile(r"^\+?\d{10,15}$")

_NAME_RE = re.compile(r"^[А-ЯЁа-яёA-Za-z][А-ЯЁа-яёA-Za-z\-\s']{1,99}$")

MIN_ADDRESS_LENGTH = 5
MAX_ADDRESS_LENGTH = 200
MAX_BIRTH_AGE_YEARS = 120


def normalize_phone(value: str) -> str:
    """Привести российский номер телефона к формату +7XXXXXXXXXX."""
    cleaned = _PHONE_CLEAN_RE.sub("", value.strip())
    if cleaned.startswith("8") and len(cleaned) == 11:
        return "+7" + cleaned[1:]
    if cleaned.startswith("7") and len(cleaned) == 11:
        return "+" + cleaned
    return cleaned


def is_valid_phone(value: str) -> bool:
    cleaned = _PHONE_CLEAN_RE.sub("", value.strip())
    if not _PHONE_DIGITS_RE.match(cleaned):
        return False
    digits = cleaned.lstrip("+")
    # отсекаем явный мусор вроде "+11111111111"
    return len(set(digits)) > 1


def is_valid_name(value: str) -> bool:
    return bool(_NAME_RE.match(value.strip()))


def is_valid_address(value: str) -> bool:
    value = value.strip()
    if not (MIN_ADDRESS_LENGTH <= len(value) <= MAX_ADDRESS_LENGTH):
        return False
    return any(ch.isdigit() for ch in value)


def is_valid_birth_date(raw: str) -> bool:
    try:
        date = datetime.strptime(raw.strip(), "%d.%m.%Y").date()
    except ValueError:
        return False
    today = now().date()
    if date > today:
        return False
    return date.year >= today.year - MAX_BIRTH_AGE_YEARS


def is_valid_event_date(raw: str) -> bool:
    """Дата напоминания: ДД.ММ или ДД.ММ.ГГГГ."""
    raw = raw.strip()
    for fmt in ("%d.%m.%Y", "%d.%m"):
        try:
            datetime.strptime(raw, fmt)
            return True
        except ValueError:
            continue
    return False
