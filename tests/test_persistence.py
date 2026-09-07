import sys
import uuid
from pathlib import Path
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "Main App"))

import sqlite3
from services.persistence.exercise_repository import (
    init_db,
    get_or_create_user,
    add_exercise,
    get_users_exercises,
    log_form_event,
    get_form_events_for_session,
    get_user_stats,
    create_workout_session,
)


@pytest.fixture(autouse=True)
def setup_db():
    init_db()
    yield


def _new_user_id():
    return str(uuid.uuid4())


def test_add_and_retrieve_exercise():
    uid = _new_user_id()
    add_exercise(uid, "Squats", reps=10, sets=1, time_sec=30.0)
    exercises = get_users_exercises(uid)
    assert len(exercises) >= 1
    names = [e["exercise_name"] for e in exercises]
    assert "Squats" in names


def test_exercise_aggregates_same_day():
    uid = _new_user_id()
    add_exercise(uid, "Push-ups", reps=5, sets=1, time_sec=15.0)
    add_exercise(uid, "Push-ups", reps=5, sets=1, time_sec=15.0)
    exercises = get_users_exercises(uid)
    pushup_records = [e for e in exercises if e["exercise_name"] == "Push-ups"]
    # Should aggregate into one row with reps=10 for the same day
    assert any(e["reps"] >= 10 for e in pushup_records)


def test_form_event_logged():
    session_id = str(uuid.uuid4())
    log_form_event(session_id, "Squats", "form_flaw", "back_lean", 45.0, "You are leaning forward.")
    events = get_form_events_for_session(session_id)
    assert len(events) >= 1
    assert events[0]["metric_name"] == "back_lean"


def test_form_event_cooldown():
    """Second log within cooldown period should be silently dropped."""
    session_id = str(uuid.uuid4())
    log_form_event(session_id, "Squats", "form_flaw", "hip_sag", 0.1, "Hip sag detected.")
    log_form_event(session_id, "Squats", "form_flaw", "hip_sag", 0.1, "Hip sag detected again.")
    events = get_form_events_for_session(session_id)
    hip_events = [e for e in events if e["metric_name"] == "hip_sag"]
    assert len(hip_events) == 1  # Second one was suppressed by cooldown


def test_user_stats_empty():
    uid = _new_user_id()
    stats = get_user_stats(uid)
    assert stats["total_reps"] == 0
    assert stats["favorite_exercise"] == "—"


def test_user_stats_populated():
    uid = _new_user_id()
    add_exercise(uid, "Squats", reps=20, sets=2, time_sec=60.0)
    add_exercise(uid, "Push-ups", reps=10, sets=1, time_sec=30.0)
    stats = get_user_stats(uid)
    assert stats["total_reps"] >= 30
    assert stats["favorite_exercise"] == "Squats"
