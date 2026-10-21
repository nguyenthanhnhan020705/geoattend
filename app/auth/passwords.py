import re
from argon2 import PasswordHasher, Type
from argon2.exceptions import VerificationError, InvalidHashError
from app.errors import ApiError

hasher = PasswordHasher(type=Type.ID)


def normalize_username(value):
    normalized = value.strip().lower()
    if not re.fullmatch(r'[a-z0-9._-]{3,50}', normalized):
        raise ApiError(422,'INVALID_USERNAME','Tên tài khoản gồm 3–50 chữ không dấu, số, dấu chấm, gạch dưới hoặc gạch ngang.')
    return normalized


def validate_password(value):
    if not 8 <= len(value) <= 128:
        raise ApiError(422,'INVALID_PASSWORD','Mật khẩu phải dài 8–128 ký tự.')
    return value


def hash_password(value):
    return hasher.hash(validate_password(value))


def verify_password(encoded, value):
    try:
        return hasher.verify(encoded, value)
    except (VerificationError, InvalidHashError):
        return False


def validate_full_name(value):
    name = value.strip()
    if not 1 <= len(name) <= 200:
        raise ApiError(422,'INVALID_NAME','Họ tên phải dài 1–200 ký tự.')
    return name
