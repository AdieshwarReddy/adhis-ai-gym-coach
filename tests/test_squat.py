import sys
from pathlib import Path
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "Main App"))

from detectors.squat import SquatDetector
from tests.mock_landmarks import create_blank_landmarks, set_point


def test_squat_full_rep_cycle():
    detector = SquatDetector()
    landmarks = create_blank_landmarks()

    # Standing: Hip=(0.5, 0.5), Knee=(0.5, 0.7), Ankle=(0.5, 0.9) -> 180 degrees
    set_point(landmarks, SquatDetector.LEFT_HIP, 0.5, 0.5)
    set_point(landmarks, SquatDetector.LEFT_KNEE, 0.5, 0.7)
    set_point(landmarks, SquatDetector.LEFT_ANKLE, 0.5, 0.9)
    set_point(landmarks, SquatDetector.LEFT_SHOULDER, 0.5, 0.2)
    set_point(landmarks, SquatDetector.RIGHT_KNEE, 0.5, 0.7, visibility=0.1)

    res = detector.process(landmarks)
    assert res["reps"] == 0
    assert res["knee_angle"] >= 160

    # Squat DOWN: Hip=(0.4, 0.7), Knee=(0.5, 0.7), Ankle=(0.5, 0.9) -> Knee is 90 degrees (< 100)
    set_point(landmarks, SquatDetector.LEFT_HIP, 0.4, 0.7)
    res = detector.process(landmarks)
    assert res["reps"] == 0
    assert detector.stage == "down"
    assert res["depth_status"] == "GOOD DEPTH"
    assert res["knee_angle"] < 100

    # Stand UP: Hip back to (0.5, 0.5) -> Knee angle ~180 degrees
    set_point(landmarks, SquatDetector.LEFT_HIP, 0.5, 0.5)
    res = detector.process(landmarks)
    assert res["reps"] == 1
    assert detector.stage == "up"
    assert res["knee_angle"] >= 160


def test_squat_partial_rep_rejected():
    detector = SquatDetector()
    landmarks = create_blank_landmarks()

    # Standing
    set_point(landmarks, SquatDetector.LEFT_HIP, 0.5, 0.5)
    set_point(landmarks, SquatDetector.LEFT_KNEE, 0.5, 0.7)
    set_point(landmarks, SquatDetector.LEFT_ANKLE, 0.5, 0.9)
    set_point(landmarks, SquatDetector.LEFT_SHOULDER, 0.5, 0.2)
    set_point(landmarks, SquatDetector.RIGHT_KNEE, 0.5, 0.7, visibility=0.1)

    detector.process(landmarks)

    # Partial squat: Knee angle ~130 degrees (does not reach < 100 degrees)
    set_point(landmarks, SquatDetector.LEFT_HIP, 0.46, 0.58)
    res = detector.process(landmarks)
    assert detector.stage is None  # Should not enter "down"
    assert res["reps"] == 0

    # Return to standing
    set_point(landmarks, SquatDetector.LEFT_HIP, 0.5, 0.5)
    res = detector.process(landmarks)
    assert res["reps"] == 0


def test_squat_reset():
    detector = SquatDetector()
    detector.reps = 5
    detector.stage = "down"
    detector.reset()
    assert detector.reps == 0
    assert detector.stage is None
