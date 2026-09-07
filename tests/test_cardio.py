import sys
import uuid
from pathlib import Path
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "Main App"))

from services.cardio.geolocation import (
    haversine_distance,
    is_valid_gps_point,
    calculate_pace,
    calculate_speed_kmh,
    format_duration
)
from services.cardio.tracker import CardioTracker
from services.persistence.exercise_repository import (
    init_db,
    create_cardio_session,
    add_cardio_route_point,
    complete_cardio_session,
    get_user_cardio_sessions,
    get_cardio_route_points,
    delete_cardio_session,
    save_transformation_record,
    get_transformation_records
)


@pytest.fixture(autouse=True)
def setup():
    init_db()
    yield


def test_haversine_distance():
    # Distance between points roughly 1km apart
    lat1, lon1 = 17.385044, 78.486671
    lat2, lon2 = 17.394044, 78.486671  # ~1000m north
    dist = haversine_distance(lat1, lon1, lat2, lon2)
    assert 990.0 < dist < 1010.0


def test_gps_filter_rejects_poor_accuracy():
    # Accuracy 80m > 50m threshold
    valid, reason = is_valid_gps_point(17.385, 78.486, accuracy=85.0, max_accuracy_meters=50.0)
    assert not valid
    assert "accuracy too low" in reason


def test_gps_filter_rejects_impossible_jump():
    last = {
        "latitude": 17.385,
        "longitude": 78.486,
        "timestamp": 100.0,
        "current_timestamp": 101.0  # 1 sec later
    }
    # Jump 500 meters in 1 second = 500 m/s (1800 km/h) -> impossible for a runner
    valid, reason = is_valid_gps_point(17.3895, 78.486, accuracy=10.0, last_point=last)
    assert not valid
    assert "Impossible speed jump" in reason


def test_calculate_pace_and_speed():
    # 1000m in 300s (5 mins) = 5:00 /km and 12.0 km/h
    sec_per_km, pace_str = calculate_pace(300, 1000)
    assert sec_per_km == 300.0
    assert pace_str == "05:00 /km"

    speed = calculate_speed_kmh(300, 1000)
    assert speed == 12.0

    assert format_duration(3665) == "01:01:05"
    assert format_duration(125) == "02:05"


def test_cardio_tracker_lifecycle():
    tracker = CardioTracker(activity_type="Running")
    assert tracker.status == "idle"

    tracker.start()
    assert tracker.status == "tracking"

    # Add point 1
    p1 = tracker.add_gps_sample(17.3850, 78.4860, accuracy=5.0, timestamp=1000.0)
    assert p1 is True

    # Add point 2 (~111m north)
    p2 = tracker.add_gps_sample(17.3860, 78.4860, accuracy=5.0, timestamp=1020.0)
    assert p2 is True
    assert tracker.distance_meters > 100.0

    # Pause
    tracker.pause()
    assert tracker.status == "paused"
    # Point during pause should not be added to active distance
    p_paused = tracker.add_gps_sample(17.3870, 78.4860, accuracy=5.0, timestamp=1030.0)
    assert p_paused is False

    # Resume & Finish
    tracker.resume()
    assert tracker.status == "tracking"
    tracker.finish()
    assert tracker.status == "completed"

    summary = tracker.get_summary()
    assert summary["activity_type"] == "Running"
    assert summary["status"] == "completed"
    assert summary["distance_km"] > 0.1


def test_cardio_persistence():
    uid = str(uuid.uuid4())
    session_id = create_cardio_session(uid, "Running")
    assert session_id is not None

    add_cardio_route_point(session_id, 1, 17.385, 78.486, 5.0, 3.2)
    add_cardio_route_point(session_id, 2, 17.386, 78.486, 4.0, 3.5)

    complete_cardio_session(session_id, elapsed_sec=600, moving_sec=550, distance_meters=2000.0, average_speed_kmh=12.0, average_pace_sec=300.0)

    sessions = get_user_cardio_sessions(uid)
    assert len(sessions) == 1
    assert sessions[0]["distance_meters"] == 2000.0

    points = get_cardio_route_points(session_id)
    assert len(points) == 2

    # Delete session
    del_ok = delete_cardio_session(session_id)
    assert del_ok is True
    assert len(get_user_cardio_sessions(uid)) == 0
    assert len(get_cardio_route_points(session_id)) == 0


def test_transformation_records_persistence():
    uid = str(uuid.uuid4())
    ok = save_transformation_record(
        user_id=uid,
        weight_kg=78.5,
        body_fat_pct=16.5,
        chest_cm=102.0,
        waist_cm=82.0,
        arms_cm=37.5,
        notes="Week 1 milestone reached!"
    )
    assert ok is True

    records = get_transformation_records(uid)
    assert len(records) == 1
    assert records[0]["weight_kg"] == 78.5
    assert records[0]["notes"] == "Week 1 milestone reached!"
