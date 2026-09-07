import os
import streamlit as st
from typing import Optional, Dict, Any, List

_SUPABASE_CLIENT = None
_INIT_ATTEMPTED = False


def get_supabase_client():
    global _SUPABASE_CLIENT, _INIT_ATTEMPTED
    if _INIT_ATTEMPTED:
        return _SUPABASE_CLIENT

    _INIT_ATTEMPTED = True
    url = os.environ.get("SUPABASE_URL", "")
    key = os.environ.get("SUPABASE_KEY", "") or os.environ.get("SUPABASE_ANON_KEY", "")

    try:
        if not url and hasattr(st, "secrets") and "SUPABASE_URL" in st.secrets:
            url = st.secrets["SUPABASE_URL"]
        if not key and hasattr(st, "secrets"):
            key = st.secrets.get("SUPABASE_KEY", "") or st.secrets.get("SUPABASE_ANON_KEY", "")
    except Exception:
        pass

    if not url or not key:
        return None

    try:
        from supabase import create_client, Client
        _SUPABASE_CLIENT = create_client(url, key)
        return _SUPABASE_CLIENT
    except Exception as e:
        print(f"Supabase client initialization warning: {e}")
        return None


def supabase_get_or_create_user(username: str) -> Optional[Dict[str, Any]]:
    client = get_supabase_client()
    if not client:
        return None

    try:
        res = client.table("profiles").select("*").eq("username", username).execute()
        if res.data and len(res.data) > 0:
            return res.data[0]

        new_user = {"username": username}
        insert_res = client.table("profiles").insert(new_user).execute()
        if insert_res.data and len(insert_res.data) > 0:
            return insert_res.data[0]
    except Exception as e:
        print(f"Supabase user operation failed, falling back to SQLite: {e}")
    return None


def supabase_add_exercise(user_id: Any, exercise_name: str, reps: int, sets: int, duration_sec: float) -> bool:
    client = get_supabase_client()
    if not client:
        return False

    try:
        record = {
            "user_id": str(user_id),
            "exercise_name": exercise_name,
            "reps": int(reps),
            "sets": int(sets),
            "time": float(duration_sec),
        }
        client.table("exercises").insert(record).execute()
        return True
    except Exception as e:
        print(f"Supabase add_exercise failed, falling back to SQLite: {e}")
        return False


def supabase_get_users_exercises(user_id: Any) -> Optional[List[Dict[str, Any]]]:
    client = get_supabase_client()
    if not client:
        return None

    try:
        res = client.table("exercises").select("*").eq("user_id", str(user_id)).order("created_at", desc=True).execute()
        return res.data if res.data is not None else []
    except Exception as e:
        print(f"Supabase get_users_exercises failed: {e}")
        return None
