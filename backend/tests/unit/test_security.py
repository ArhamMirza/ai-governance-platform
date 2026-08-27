from app.core.security import (
    generate_session_token,
    hash_password,
    hash_session_token,
    verify_password,
)


def test_hash_password_is_not_the_plaintext() -> None:
    assert hash_password("hunter2") != "hunter2"


def test_verify_password_accepts_the_correct_password() -> None:
    hashed = hash_password("hunter2")

    assert verify_password("hunter2", hashed) is True


def test_verify_password_rejects_the_wrong_password() -> None:
    hashed = hash_password("hunter2")

    assert verify_password("wrong", hashed) is False


def test_hash_password_salts_every_call_differently() -> None:
    assert hash_password("hunter2") != hash_password("hunter2")


def test_verify_password_rejects_a_malformed_hash() -> None:
    assert verify_password("hunter2", "not-a-real-hash") is False


def test_generate_session_token_is_unique_per_call() -> None:
    assert generate_session_token() != generate_session_token()


def test_hash_session_token_is_deterministic() -> None:
    token = generate_session_token()

    assert hash_session_token(token) == hash_session_token(token)


def test_hash_session_token_differs_for_different_tokens() -> None:
    assert hash_session_token("token-a") != hash_session_token("token-b")
