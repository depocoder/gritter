from gritter.services.auth.password import hash_password, verify_password


def test_hash_password_is_not_plaintext() -> None:
    digest = hash_password("hunter22-plus-extra")
    assert digest != "hunter22-plus-extra"
    assert digest.startswith("$argon2")


def test_verify_password_accepts_correct_password() -> None:
    digest = hash_password("correct-horse-battery")
    assert verify_password("correct-horse-battery", digest) is True


def test_verify_password_rejects_wrong_password() -> None:
    digest = hash_password("correct-horse-battery")
    assert verify_password("nope", digest) is False
