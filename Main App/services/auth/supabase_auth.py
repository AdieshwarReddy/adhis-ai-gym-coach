import hashlib
import os
import sqlite3
from typing import Optional, Dict, Any
from pathlib import Path
from services.config.env_config import get_supabase_url, get_supabase_anon_key

_DB_PATH = Path(__file__).resolve().parent.parent.parent / "data.db"


def _get_supabase_client():
    url = get_supabase_url()
    key = get_supabase_anon_key()
    if url and key:
        try:
            from supabase import create_client, Client
            return create_client(url, key)
        except Exception:
            return None
    return None


def is_cloud_auth_enabled() -> bool:
    return _get_supabase_client() is not None


def _hash_password(password: str) -> str:
    """Simple SHA-256 password hashing for offline local SQLite fallback."""
    salt = "adhi_gym_coach_salt_2026"
    return hashlib.sha256((password + salt).encode("utf-8")).hexdigest()


def sign_up(email: str, password: str, display_name: str) -> Dict[str, Any]:
    """
    Registers a new user via Supabase Auth or local SQLite fallback.
    Returns {"success": bool, "user": dict, "error": str}.
    """
    email = email.strip().lower()
    display_name = display_name.strip()

    if not email or "@" not in email:
        return {"success": False, "error": "Please enter a valid email address."}
    if len(password) < 6:
        return {"success": False, "error": "Password must be at least 6 characters long."}
    if not display_name:
        return {"success": False, "error": "Please provide a display name."}

    client = _get_supabase_client()

    if client:
        try:
            response = client.auth.sign_up({
                "email": email,
                "password": password,
                "options": {
                    "data": {"display_name": display_name}
                }
            })
            if response.user:
                # Ensure profile exists in profiles table
                try:
                    client.table("profiles").upsert({
                        "id": response.user.id,
                        "auth_user_id": response.user.id,
                        "display_name": display_name
                    }).execute()
                except Exception:
                    pass

                return {
                    "success": True,
                    "user": {
                        "id": response.user.id,
                        "email": response.user.email,
                        "display_name": display_name,
                        "is_cloud": True
                    },
                    "error": None
                }
            return {"success": False, "error": "Failed to create account. Please check your details."}
        except Exception as e:
            err_msg = str(e).lower()
            if "already registered" in err_msg or "unique" in err_msg:
                return {"success": False, "error": "An account with this email already exists."}
            return {"success": False, "error": f"Registration failed: {str(e)}"}

    # Local SQLite Fallback
    try:
        conn = sqlite3.connect(str(_DB_PATH))
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS local_users (
                id TEXT PRIMARY KEY,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                display_name TEXT NOT NULL,
                age INTEGER DEFAULT NULL,
                height_cm REAL DEFAULT NULL,
                experience_level TEXT DEFAULT 'Beginner',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        import uuid
        user_id = str(uuid.uuid4())
        pwd_hash = _hash_password(password)

        cursor.execute(
            "INSERT INTO local_users (id, email, password_hash, display_name) VALUES (?, ?, ?, ?)",
            (user_id, email, pwd_hash, display_name)
        )
        conn.commit()
        conn.close()

        return {
            "success": True,
            "user": {
                "id": user_id,
                "email": email,
                "display_name": display_name,
                "is_cloud": False
            },
            "error": None
        }
    except sqlite3.IntegrityError:
        return {"success": False, "error": "An account with this email already exists."}
    except Exception as e:
        return {"success": False, "error": f"Local signup error: {str(e)}"}


def sign_in(email: str, password: str) -> Dict[str, Any]:
    """
    Authenticates an existing user via Supabase Auth or local SQLite fallback.
    """
    email = email.strip().lower()

    if not email or not password:
        return {"success": False, "error": "Please enter both email and password."}

    client = _get_supabase_client()

    if client:
        try:
            response = client.auth.sign_in_with_password({
                "email": email,
                "password": password
            })
            if response.user:
                display_name = response.user.user_metadata.get("display_name", email.split("@")[0])
                return {
                    "success": True,
                    "user": {
                        "id": response.user.id,
                        "email": response.user.email,
                        "display_name": display_name,
                        "is_cloud": True
                    },
                    "error": None
                }
            return {"success": False, "error": "Invalid email or password."}
        except Exception as e:
            err_msg = str(e).lower()
            if "invalid" in err_msg or "credentials" in err_msg:
                return {"success": False, "error": "Invalid email or password. Please try again."}
            return {"success": False, "error": f"Login failed: {str(e)}"}

    # Local SQLite Fallback
    try:
        conn = sqlite3.connect(str(_DB_PATH))
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, email, password_hash, display_name FROM local_users WHERE email = ?",
            (email,)
        )
        row = cursor.fetchone()
        conn.close()

        if row:
            stored_hash = row[2]
            if _hash_password(password) == stored_hash:
                return {
                    "success": True,
                    "user": {
                        "id": row[0],
                        "email": row[1],
                        "display_name": row[3],
                        "is_cloud": False
                    },
                    "error": None
                }
        return {"success": False, "error": "Invalid email or password."}
    except Exception as e:
        return {"success": False, "error": f"Local login error: {str(e)}"}


def reset_password(email: str) -> Dict[str, Any]:
    """Sends a password recovery email if cloud auth is configured."""
    client = _get_supabase_client()
    if client:
        try:
            client.auth.reset_password_for_email(email)
            return {"success": True, "message": "Password reset instructions sent to your email."}
        except Exception as e:
            return {"success": False, "error": str(e)}
    return {"success": True, "message": "In offline/local mode, reset password by creating a new account."}
