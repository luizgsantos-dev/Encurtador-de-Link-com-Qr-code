import secrets
import string

ALPHABET = string.ascii_letters + string.digits
DEFAULT_LENGTH = 6


def generate_short_code(length: int = DEFAULT_LENGTH) -> str:
    return "".join(secrets.choice(ALPHABET) for _ in range(length))
