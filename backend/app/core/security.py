"""
UniSphere Password Security Module.

Implements password hashing and verification using the Argon2id algorithm
via argon2-cffi, following OWASP security standards.
"""

from typing import Optional
from argon2 import PasswordHasher, Type
from argon2.exceptions import (
    InvalidHashError,
    VerificationError,
    VerifyMismatchError,
)

# Argon2id password hasher with parameters aligned to OWASP recommendations:
# - Type: Argon2id (hybrid resistant to both side-channel and GPU cracking)
# - Memory cost: 65,536 KiB (64 MiB)
# - Time cost: 3 iterations
# - Parallelism: 4 threads
# - Salt length: 16 bytes (unique cryptographically secure salt generated per hash)
# - Hash length: 32 bytes
_hasher = PasswordHasher(
    time_cost=3,
    memory_cost=65536,
    parallelism=4,
    hash_len=32,
    salt_len=16,
    type=Type.ID,
)


def hash_password(plain_password: str) -> str:
    """
    Hash a plaintext password using Argon2id.

    Generates a unique salt for each call and returns the formatted
    encoded hash string ($argon2id$v=19$m=65536,t=3,p=4$...).

    Raises:
        ValueError: If plain_password is empty or not a string.
    """
    if not isinstance(plain_password, str) or not plain_password:
        raise ValueError("Password must be a non-empty string.")

    return _hasher.hash(plain_password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a plaintext password against an Argon2 hash.

    Returns:
        True if the password matches the hash, False otherwise.
        Returns False safely on any mismatch or malformed hash without
        leaking internal exception details.
    """
    if not isinstance(plain_password, str) or not plain_password:
        return False

    if not isinstance(hashed_password, str) or not hashed_password:
        return False

    try:
        return _hasher.verify(hashed_password, plain_password)
    except (VerifyMismatchError, VerificationError, InvalidHashError):
        return False


def needs_rehash(hashed_password: str) -> bool:
    """
    Check whether a given hash was created using outdated parameters.

    Returns True if the hash should be re-generated with current parameters,
    or if the provided hash is malformed or invalid.
    """
    if not isinstance(hashed_password, str) or not hashed_password:
        return True

    try:
        return _hasher.check_needs_rehash(hashed_password)
    except (InvalidHashError, VerificationError, ValueError):
        return True
