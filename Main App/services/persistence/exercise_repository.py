"""
Supabase / SQLite Dual-Mode Persistence Layer
=============================================
All database operations route through this module.
- If SUPABASE_URL + SUPABASE_ANON_KEY are configured → Supabase PostgreSQL (cloud, with RLS).
- Otherwise → local SQLite (Main App/data.db) for offline / dev mode.

Tables used:
  Supabase: profiles, workout_sessions, exercise_sets, form_events, workout_summaries
  SQLite  : local_users, exercises (flat schema, backward-compatible)
"""
import sqlite3
import uuid
import time as _time
from pathlib import Path
from typing import Dict, Any, List, Optional, Union

import streamlit as st

from services.config.env_config import get_supabase_url, get_supabase_anon_key

# ── Database path ────────────────────────────────────────────────────────────
_DB_PATH = str(Path(__file__).resolve().parent.parent.parent / "data.db")


# ─────────────────────────────────────────────────────────────────────────────
# Supabase Client (singleton, lazy init)
# ─────────────────────────────────────────────────────────────────────────────
_supabase_client = None
_supabase_init_done = False


def get_supabase_client():
    global _supabase_client, _supabase_init_done
    if _supabase_init_done:
        return _supabase_client
    _supabase_init_done = True

    url = get_supabase_url()
    key = get_supabase_anon_key()
    if not url or not key:
        return None

    try:
        from supabase import create_client
        _supabase_client = create_client(url, key)
        return _supabase_client
    except Exception:
        return None


def is_cloud_mode() -> bool:
    return get_supabase_client() is not None


# ─────────────────────────────────────────────────────────────────────────────
# SQLite Connection (singleton, cached)
# ─────────────────────────────────────────────────────────────────────────────
@st.cache_resource
def _get_sqlite_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(_DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    """Initialize local SQLite tables for offline / dev mode."""
    conn = _get_sqlite_conn()
    with conn:
        conn.execute("""
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
        conn.execute("""
            CREATE TABLE IF NOT EXISTS exercises (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                exercise_name TEXT NOT NULL,
                reps INTEGER NOT NULL DEFAULT 0,
                sets INTEGER NOT NULL DEFAULT 0,
                time INTEGER NOT NULL DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS workout_sessions_local (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                completed_at TIMESTAMP,
                duration_seconds INTEGER DEFAULT 0,
                status TEXT DEFAULT 'in_progress'
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS form_events_local (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                exercise_type TEXT NOT NULL,
                event_type TEXT NOT NULL,
                metric_name TEXT,
                metric_value REAL,
                message TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS cardio_sessions_local (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                activity_type TEXT NOT NULL,
                started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                completed_at TIMESTAMP,
                elapsed_seconds INTEGER DEFAULT 0,
                moving_seconds INTEGER DEFAULT 0,
                distance_meters REAL DEFAULT 0.0,
                average_speed_kmh REAL DEFAULT 0.0,
                average_pace_sec_per_km REAL DEFAULT 0.0,
                status TEXT DEFAULT 'in_progress'
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS cardio_route_points_local (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                sequence_number INTEGER NOT NULL,
                latitude REAL NOT NULL,
                longitude REAL NOT NULL,
                accuracy_meters REAL,
                speed_mps REAL,
                recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS transformations_local (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                recorded_date DATE DEFAULT (date('now')),
                weight_kg REAL,
                body_fat_pct REAL,
                chest_cm REAL,
                waist_cm REAL,
                arms_cm REAL,
                notes TEXT,
                before_img_data TEXT,
                after_img_data TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)


# ─────────────────────────────────────────────────────────────────────────────
# Legacy compatibility shim (for existing session_state lookups)
# ─────────────────────────────────────────────────────────────────────────────
def get_or_create_user(username: str) -> Dict[str, Any]:
    """LEGACY – kept for backward compatibility. Use sign_up/sign_in instead."""
    conn = _get_sqlite_conn()
    row = conn.execute("SELECT id, display_name FROM local_users WHERE display_name = ?", (username,)).fetchone()
    if row:
        return {"id": row["id"], "username": row["display_name"]}
    user_id = str(uuid.uuid4())
    import hashlib
    pwd_hash = hashlib.sha256(("legacy_" + username + "_salt").encode()).hexdigest()
    with conn:
        conn.execute(
            "INSERT OR IGNORE INTO local_users (id, email, password_hash, display_name) VALUES (?, ?, ?, ?)",
            (user_id, f"{username}@local.adhigym", pwd_hash, username)
        )
    return {"id": user_id, "username": username}


# ─────────────────────────────────────────────────────────────────────────────
# WORKOUT SESSION LIFECYCLE
# ─────────────────────────────────────────────────────────────────────────────
def create_workout_session(user_id: str) -> Optional[str]:
    """
    Creates a new workout session record.
    Returns the session_id (UUID string) or None on failure.
    """
    session_id = str(uuid.uuid4())
    client = get_supabase_client()

    if client:
        try:
            # Need profile UUID to link session
            profile_res = client.table("profiles").select("id").eq("auth_user_id", user_id).execute()
            profile_id = profile_res.data[0]["id"] if profile_res.data else user_id

            client.table("workout_sessions").insert({
                "id": session_id,
                "user_id": profile_id,
                "status": "in_progress"
            }).execute()
            return session_id
        except Exception:
            pass  # Fall through to SQLite

    # SQLite fallback
    try:
        conn = _get_sqlite_conn()
        with conn:
            conn.execute(
                "INSERT INTO workout_sessions_local (id, user_id) VALUES (?, ?)",
                (session_id, str(user_id))
            )
        return session_id
    except Exception:
        return session_id  # Return it anyway; logging is best-effort


def complete_workout_session(session_id: str, duration_seconds: int) -> None:
    """Marks session as completed with final duration."""
    client = get_supabase_client()
    if client:
        try:
            from datetime import datetime, timezone
            client.table("workout_sessions").update({
                "status": "completed",
                "completed_at": datetime.now(timezone.utc).isoformat(),
                "duration_seconds": duration_seconds
            }).eq("id", session_id).execute()
            return
        except Exception:
            pass

    try:
        conn = _get_sqlite_conn()
        with conn:
            conn.execute(
                "UPDATE workout_sessions_local SET status='completed', duration_seconds=? WHERE id=?",
                (duration_seconds, session_id)
            )
    except Exception:
        pass


# ─────────────────────────────────────────────────────────────────────────────
# EXERCISE SETS
# ─────────────────────────────────────────────────────────────────────────────
def add_exercise(user_id: Union[int, str], exercise_name: str, reps: int, sets: int, time_sec: float,
                 session_id: Optional[str] = None, set_number: int = 1, target_reps: int = 0) -> None:
    """
    Saves a completed exercise set.
    Writes to Supabase (exercise_sets + exercises) and always syncs to SQLite.
    """
    client = get_supabase_client()
    if client and session_id:
        try:
            from datetime import datetime, timezone
            client.table("exercise_sets").insert({
                "id": str(uuid.uuid4()),
                "session_id": session_id,
                "exercise_type": exercise_name,
                "set_number": set_number,
                "target_reps": target_reps if target_reps > 0 else reps,
                "completed_reps": reps,
                "completed_at": datetime.now(timezone.utc).isoformat()
            }).execute()
        except Exception:
            pass  # Non-fatal; local SQLite will persist below

    # SQLite dual-write
    try:
        conn = _get_sqlite_conn()
        str_user_id = str(user_id)
        with conn:
            existing = conn.execute(
                "SELECT id, reps, sets, time FROM exercises WHERE user_id=? AND exercise_name=? AND date(created_at)=date('now')",
                (str_user_id, exercise_name)
            ).fetchone()
            if existing:
                conn.execute(
                    "UPDATE exercises SET reps=reps+?, sets=sets+?, time=time+? WHERE id=?",
                    (reps, sets, int(time_sec), existing["id"])
                )
            else:
                conn.execute(
                    "INSERT INTO exercises (user_id, exercise_name, reps, sets, time) VALUES (?, ?, ?, ?, ?)",
                    (str_user_id, exercise_name, reps, sets, int(time_sec))
                )
    except Exception:
        pass


def get_users_exercises(user_id: Union[int, str]) -> List[Dict[str, Any]]:
    """
    Retrieves historical exercise records for a given user.
    Prefers Supabase; falls back to SQLite.
    """
    client = get_supabase_client()
    if client:
        try:
            # Try to get exercise_sets via workout_sessions (normalized path)
            profile_res = client.table("profiles").select("id").eq("auth_user_id", str(user_id)).execute()
            if profile_res.data:
                profile_id = profile_res.data[0]["id"]
                sessions_res = client.table("workout_sessions").select("id").eq("user_id", profile_id).execute()
                session_ids = [s["id"] for s in sessions_res.data] if sessions_res.data else []
                if session_ids:
                    sets_res = (
                        client.table("exercise_sets")
                        .select("exercise_type, completed_reps, set_number, completed_at, target_reps")
                        .in_("session_id", session_ids)
                        .order("completed_at", desc=True)
                        .execute()
                    )
                    if sets_res.data:
                        return [
                            {
                                "exercise_name": row["exercise_type"],
                                "reps": row["completed_reps"],
                                "sets": 1,
                                "time": 0,
                                "created_at": row.get("completed_at", "")
                            }
                            for row in sets_res.data
                        ]
        except Exception:
            pass

    # SQLite fallback
    try:
        conn = _get_sqlite_conn()
        rows = conn.execute(
            "SELECT * FROM exercises WHERE user_id=? ORDER BY created_at DESC",
            (str(user_id),)
        ).fetchall()
        return [dict(r) for r in rows]
    except Exception:
        return []


# ─────────────────────────────────────────────────────────────────────────────
# FORM EVENTS (Debounced)
# ─────────────────────────────────────────────────────────────────────────────
_form_event_cooldown: Dict[str, float] = {}
FORM_EVENT_COOLDOWN_SECONDS = 2.0


def log_form_event(session_id: Optional[str], exercise_type: str, event_type: str,
                   metric_name: str, metric_value: Optional[float], message: str) -> None:
    """
    Logs a form quality event with a per-metric cooldown to prevent frame-rate spam.
    Only one event per metric type fires at most once every 2 seconds.
    """
    now = _time.time()
    cooldown_key = f"{session_id}:{metric_name}"
    if now - _form_event_cooldown.get(cooldown_key, 0) < FORM_EVENT_COOLDOWN_SECONDS:
        return
    _form_event_cooldown[cooldown_key] = now

    client = get_supabase_client()
    if client and session_id:
        try:
            client.table("form_events").insert({
                "id": str(uuid.uuid4()),
                "session_id": session_id,
                "exercise_type": exercise_type,
                "event_type": event_type,
                "metric_name": metric_name,
                "metric_value": metric_value,
                "message": message
            }).execute()
            return
        except Exception:
            pass

    # SQLite fallback
    try:
        conn = _get_sqlite_conn()
        with conn:
            conn.execute(
                "INSERT INTO form_events_local (session_id, exercise_type, event_type, metric_name, metric_value, message) VALUES (?, ?, ?, ?, ?, ?)",
                (str(session_id or "local"), exercise_type, event_type, metric_name, metric_value, message)
            )
    except Exception:
        pass


def get_form_events_for_session(session_id: str) -> List[Dict[str, Any]]:
    """Returns all form events logged for a given session."""
    client = get_supabase_client()
    if client and session_id:
        try:
            res = client.table("form_events").select("*").eq("session_id", session_id).order("created_at").execute()
            return res.data or []
        except Exception:
            pass
    try:
        conn = _get_sqlite_conn()
        rows = conn.execute(
            "SELECT * FROM form_events_local WHERE session_id=? ORDER BY created_at",
            (session_id,)
        ).fetchall()
        return [dict(r) for r in rows]
    except Exception:
        return []


# ─────────────────────────────────────────────────────────────────────────────
# WORKOUT SUMMARIES
# ─────────────────────────────────────────────────────────────────────────────
def save_workout_summary(session_id: str, total_reps: int, completed_sets: int,
                         duration_seconds: int, coach_summary: str) -> None:
    """Saves the AI-generated post-workout summary alongside session metrics."""
    client = get_supabase_client()
    if client:
        try:
            client.table("workout_summaries").upsert({
                "id": str(uuid.uuid4()),
                "session_id": session_id,
                "total_reps": total_reps,
                "completed_sets": completed_sets,
                "duration_seconds": duration_seconds,
                "coach_summary": coach_summary
            }).execute()
            return
        except Exception:
            pass


def get_workout_summary(session_id: str) -> Optional[Dict[str, Any]]:
    """Retrieves the summary for a given session."""
    client = get_supabase_client()
    if client:
        try:
            res = client.table("workout_summaries").select("*").eq("session_id", session_id).execute()
            return res.data[0] if res.data else None
        except Exception:
            pass
    return None


# ─────────────────────────────────────────────────────────────────────────────
# USER PROFILE
# ─────────────────────────────────────────────────────────────────────────────
def get_user_profile(user_id: str) -> Optional[Dict[str, Any]]:
    """Retrieves the user profile record from Supabase or SQLite."""
    client = get_supabase_client()
    if client:
        try:
            res = client.table("profiles").select("*").eq("auth_user_id", user_id).execute()
            return res.data[0] if res.data else None
        except Exception:
            pass
    try:
        conn = _get_sqlite_conn()
        row = conn.execute("SELECT * FROM local_users WHERE id=?", (str(user_id),)).fetchone()
        return dict(row) if row else None
    except Exception:
        return None


def update_user_profile(user_id: str, display_name: str = None,
                        age: int = None, height_cm: float = None,
                        experience_level: str = None) -> bool:
    """Updates editable profile fields."""
    update_data: Dict[str, Any] = {}
    if display_name:
        update_data["display_name"] = display_name
    if age is not None:
        update_data["age"] = age
    if height_cm is not None:
        update_data["height_cm"] = height_cm
    if experience_level:
        update_data["experience_level"] = experience_level

    if not update_data:
        return False

    client = get_supabase_client()
    if client:
        try:
            client.table("profiles").update(update_data).eq("auth_user_id", user_id).execute()
            return True
        except Exception:
            pass

    try:
        conn = _get_sqlite_conn()
        set_clause = ", ".join(f"{k}=?" for k in update_data)
        with conn:
            conn.execute(
                f"UPDATE local_users SET {set_clause} WHERE id=?",
                (*update_data.values(), str(user_id))
            )
        return True
    except Exception:
        return False


# ─────────────────────────────────────────────────────────────────────────────
# CARDIO SESSION PERSISTENCE (Supabase + Local SQLite)
# ─────────────────────────────────────────────────────────────────────────────
def create_cardio_session(user_id: str, activity_type: str = "Running") -> str:
    """Creates a new cardio session entry and returns its UUID."""
    session_id = str(uuid.uuid4())
    client = get_supabase_client()
    if client:
        try:
            profile_res = client.table("profiles").select("id").eq("auth_user_id", str(user_id)).execute()
            profile_id = profile_res.data[0]["id"] if profile_res.data else str(user_id)
            client.table("cardio_sessions").insert({
                "id": session_id,
                "user_id": profile_id,
                "activity_type": activity_type,
                "status": "in_progress"
            }).execute()
        except Exception:
            pass

    try:
        conn = _get_sqlite_conn()
        with conn:
            conn.execute(
                "INSERT INTO cardio_sessions_local (id, user_id, activity_type, status) VALUES (?, ?, ?, 'in_progress')",
                (session_id, str(user_id), activity_type)
            )
    except Exception:
        pass
    return session_id


def add_cardio_route_point(session_id: str, seq_num: int, lat: float, lng: float, accuracy: float, speed_mps: float = 0.0) -> None:
    """Appends a recorded GPS coordinate sample to the route."""
    client = get_supabase_client()
    if client:
        try:
            client.table("cardio_route_points").insert({
                "session_id": session_id,
                "sequence_number": seq_num,
                "latitude": lat,
                "longitude": lng,
                "accuracy_meters": accuracy,
                "speed_mps": speed_mps
            }).execute()
        except Exception:
            pass

    try:
        conn = _get_sqlite_conn()
        with conn:
            conn.execute(
                """INSERT INTO cardio_route_points_local (session_id, sequence_number, latitude, longitude, accuracy_meters, speed_mps)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (session_id, seq_num, lat, lng, accuracy, speed_mps)
            )
    except Exception:
        pass


def complete_cardio_session(
    session_id: str,
    elapsed_sec: int,
    moving_sec: int,
    distance_meters: float,
    average_speed_kmh: float,
    average_pace_sec: float
) -> None:
    """Finalizes a cardio session with completed duration, distance, and averages."""
    client = get_supabase_client()
    if client:
        try:
            from datetime import datetime, timezone
            client.table("cardio_sessions").update({
                "status": "completed",
                "completed_at": datetime.now(timezone.utc).isoformat(),
                "elapsed_seconds": elapsed_sec,
                "moving_seconds": moving_sec,
                "distance_meters": distance_meters,
                "average_speed_kmh": average_speed_kmh,
                "average_pace_sec_per_km": average_pace_sec
            }).eq("id", session_id).execute()
        except Exception:
            pass

    try:
        conn = _get_sqlite_conn()
        with conn:
            conn.execute(
                """UPDATE cardio_sessions_local
                   SET status='completed', completed_at=CURRENT_TIMESTAMP,
                       elapsed_seconds=?, moving_seconds=?, distance_meters=?,
                       average_speed_kmh=?, average_pace_sec_per_km=?
                   WHERE id=?""",
                (elapsed_sec, moving_sec, distance_meters, average_speed_kmh, average_pace_sec, session_id)
            )
    except Exception:
        pass


def get_user_cardio_sessions(user_id: str) -> List[Dict[str, Any]]:
    """Retrieves all completed cardio sessions for a given user."""
    client = get_supabase_client()
    if client:
        try:
            profile_res = client.table("profiles").select("id").eq("auth_user_id", str(user_id)).execute()
            if profile_res.data:
                profile_id = profile_res.data[0]["id"]
                res = client.table("cardio_sessions").select("*").eq("user_id", profile_id).order("started_at", desc=True).execute()
                if res.data:
                    return res.data
        except Exception:
            pass

    try:
        conn = _get_sqlite_conn()
        rows = conn.execute(
            "SELECT * FROM cardio_sessions_local WHERE user_id=? ORDER BY started_at DESC",
            (str(user_id),)
        ).fetchall()
        return [dict(r) for r in rows]
    except Exception:
        return []


def get_cardio_route_points(session_id: str) -> List[Dict[str, Any]]:
    """Retrieves all ordered GPS route points for a given cardio session."""
    client = get_supabase_client()
    if client:
        try:
            res = client.table("cardio_route_points").select("*").eq("session_id", session_id).order("sequence_number").execute()
            if res.data:
                return res.data
        except Exception:
            pass

    try:
        conn = _get_sqlite_conn()
        rows = conn.execute(
            "SELECT * FROM cardio_route_points_local WHERE session_id=? ORDER BY sequence_number ASC",
            (session_id,)
        ).fetchall()
        return [dict(r) for r in rows]
    except Exception:
        return []


def delete_cardio_session(session_id: str) -> bool:
    """Deletes a cardio session and associated route points (RLS/Cascade protected)."""
    client = get_supabase_client()
    if client:
        try:
            client.table("cardio_sessions").delete().eq("id", session_id).execute()
        except Exception:
            pass

    try:
        conn = _get_sqlite_conn()
        with conn:
            conn.execute("DELETE FROM cardio_route_points_local WHERE session_id=?", (session_id,))
            conn.execute("DELETE FROM cardio_sessions_local WHERE id=?", (session_id,))
        return True
    except Exception:
        return False


# ─────────────────────────────────────────────────────────────────────────────
# RESULTS & TRANSFORMATION (Before & After Persistence)
# ─────────────────────────────────────────────────────────────────────────────
def save_transformation_record(
    user_id: str,
    weight_kg: Optional[float] = None,
    body_fat_pct: Optional[float] = None,
    chest_cm: Optional[float] = None,
    waist_cm: Optional[float] = None,
    arms_cm: Optional[float] = None,
    notes: str = "",
    before_img_data: str = "",
    after_img_data: str = ""
) -> bool:
    """Saves a transformation milestone with body metrics and optional photos."""
    try:
        conn = _get_sqlite_conn()
        with conn:
            conn.execute(
                """INSERT INTO transformations_local
                   (user_id, weight_kg, body_fat_pct, chest_cm, waist_cm, arms_cm, notes, before_img_data, after_img_data)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (str(user_id), weight_kg, body_fat_pct, chest_cm, waist_cm, arms_cm, notes, before_img_data, after_img_data)
            )
        return True
    except Exception:
        return False


def get_transformation_records(user_id: str) -> List[Dict[str, Any]]:
    """Retrieves all transformation entries logged by the user."""
    try:
        conn = _get_sqlite_conn()
        rows = conn.execute(
            "SELECT * FROM transformations_local WHERE user_id=? ORDER BY recorded_date ASC, created_at ASC",
            (str(user_id),)
        ).fetchall()
        return [dict(r) for r in rows]
    except Exception:
        return []


# ─────────────────────────────────────────────────────────────────────────────
# ANALYTICS HELPERS (Combined Strength + Cardio)
# ─────────────────────────────────────────────────────────────────────────────
def get_user_stats(user_id: str) -> Dict[str, Any]:
    """Returns high-level aggregate stats combining strength and cardio for the dashboard."""
    exercises = get_users_exercises(user_id)
    cardio_sessions = get_user_cardio_sessions(user_id)

    total_reps = sum(r.get("reps", 0) for r in exercises) if exercises else 0
    total_sets = sum(r.get("sets", 1) for r in exercises) if exercises else 0
    total_strength_time = sum(r.get("time", 0) for r in exercises) if exercises else 0

    # Cardio stats
    total_cardio_distance_m = sum(c.get("distance_meters", 0.0) for c in cardio_sessions) if cardio_sessions else 0.0
    total_cardio_time = sum(c.get("elapsed_seconds", 0) for c in cardio_sessions) if cardio_sessions else 0
    total_cardio_km = round(total_cardio_distance_m / 1000.0, 2)

    total_time_sec = int(total_strength_time + total_cardio_time)

    # Favorite strength exercise
    exercise_counts: Dict[str, int] = {}
    for r in (exercises or []):
        name = r.get("exercise_name", "Unknown")
        exercise_counts[name] = exercise_counts.get(name, 0) + r.get("reps", 0)
    favorite = max(exercise_counts, key=exercise_counts.get) if exercise_counts else "—"

    # Unique active days
    dates = set()
    for r in (exercises or []):
        created = r.get("created_at", "")
        if created:
            dates.add(str(created)[:10])
    for c in (cardio_sessions or []):
        started = c.get("started_at", "")
        if started:
            dates.add(str(started)[:10])

    return {
        "total_reps": total_reps,
        "total_sets": total_sets,
        "total_strength_workouts": len(exercises or []),
        "total_cardio_sessions": len(cardio_sessions or []),
        "total_cardio_distance_km": total_cardio_km,
        "total_workouts": max(len(dates), len(exercises or []) + len(cardio_sessions or [])),
        "total_time_sec": total_time_sec,
        "favorite_exercise": favorite,
    }

