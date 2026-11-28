"""
Unit tests for UniSphere Argon2 security module.
"""

import pytest
from app.core.security import hash_password, verify_password, needs_rehash


def test_hash_password_produces_argon2id_format():
    plain = "SuperSecretDemoPassword123!"
    hashed = hash_password(plain)

    # Must start with standard argon2id prefix
    assert hashed.startswith("$argon2id$v=19$m=65536,t=3,p=4$")
    assert plain not in hashed


def test_hash_password_generates_unique_salts():
    plain = "IdenticalPasswordForTwoUsers"
    hash1 = hash_password(plain)
    hash2 = hash_password(plain)

    # Even identical passwords must yield distinct hashes due to unique salts
    assert hash1 != hash2
    assert verify_password(plain, hash1) is True
    assert verify_password(plain, hash2) is True


def test_verify_password_success_and_failure():
    plain = "CorrectPassword2026"
    hashed = hash_password(plain)

    assert verify_password(plain, hashed) is True
    assert verify_password("WrongPassword2026", hashed) is False
    assert verify_password("", hashed) is False
    assert verify_password(plain, "") is False
    assert verify_password("test", "not_a_valid_argon2_hash") is False


def test_hash_password_rejects_empty():
    with pytest.raises(ValueError, match="Password must be a non-empty string"):
        hash_password("")

    with pytest.raises(ValueError, match="Password must be a non-empty string"):
        hash_password(None)  # type: ignore


def test_needs_rehash_behavior():
    plain = "CheckRehashPass"
    hashed = hash_password(plain)

    # A freshly generated hash with current parameters should not need rehash
    assert needs_rehash(hashed) is False
    # Invalid hash should safely return True
    assert needs_rehash("corrupted_hash") is True
