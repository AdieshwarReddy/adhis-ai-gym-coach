import sys
from pathlib import Path
import pytest
import uuid

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "Main App"))

from services.auth.supabase_auth import sign_up, sign_in, _hash_password


def test_hash_password_consistency():
    h1 = _hash_password("secret_pass")
    h2 = _hash_password("secret_pass")
    assert h1 == h2
    assert len(h1) == 64  # SHA-256


def test_local_signup_and_signin():
    test_email = f"test_{uuid.uuid4().hex[:8]}@adhigym.com"
    password = "strongpassword123"
    display_name = "Adhi Champion"

    # Sign up
    res_signup = sign_up(test_email, password, display_name)
    assert res_signup["success"] is True
    assert res_signup["user"]["email"] == test_email
    assert res_signup["user"]["display_name"] == display_name

    # Sign in with correct password
    res_signin = sign_in(test_email, password)
    assert res_signin["success"] is True
    assert res_signin["user"]["email"] == test_email

    # Sign in with wrong password
    res_fail = sign_in(test_email, "wrongpassword")
    assert res_fail["success"] is False
    assert "invalid" in res_fail["error"].lower()


def test_signup_validation():
    # Invalid email
    res1 = sign_up("invalidemail", "pass123", "Name")
    assert res1["success"] is False
    assert "email" in res1["error"].lower()

    # Password too short
    res2 = sign_up("test@example.com", "123", "Name")
    assert res2["success"] is False
    assert "6 characters" in res2["error"].lower()
