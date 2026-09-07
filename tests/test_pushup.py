import sys
from pathlib import Path
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "Main App"))

from detectors.pushup import PushUpDetector
from tests.mock_landmarks import create_blank_landmarks, set_point


def test_pushup_rep_cycle():
    detector = PushUpDetector()
    landmarks = create_blank_landmarks()

    # Plank UP:
    # Shoulder=(0.2, 0.5), Elbow=(0.2, 0.7), Wrist=(0.2, 0.9) -> Straight arm (180 deg)
    # Hip=(0.5, 0.5), Ankle=(0.8, 0.5) -> Body angle straight (180 deg)
    set_point(landmarks, PushUpDetector.LEFT_SHOULDER, 0.2, 0.5)
    set_point(landmarks, PushUpDetector.LEFT_ELBOW, 0.2, 0.7)
    set_point(landmarks, PushUpDetector.LEFT_WRIST, 0.2, 0.9)
    set_point(landmarks, PushUpDetector.LEFT_HIP, 0.5, 0.5)
    set_point(landmarks, PushUpDetector.LEFT_ANKLE, 0.8, 0.5)
    set_point(landmarks, PushUpDetector.RIGHT_ELBOW, 0.2, 0.7, visibility=0.1)

    res = detector.process(landmarks)
    assert res["reps"] == 0
    assert res["elbow_angle"] >= 160
    assert res["body_alignment"] == "Straight"
    assert res["hip_status"] == "LEVEL"

    # Lower DOWN: Elbow bends to 90 degrees or less
    # Shoulder=(0.2, 0.7), Elbow=(0.1, 0.7), Wrist=(0.2, 0.9) -> acute/right angle
    set_point(landmarks, PushUpDetector.LEFT_SHOULDER, 0.2, 0.7)
    set_point(landmarks, PushUpDetector.LEFT_ELBOW, 0.1, 0.7)
    set_point(landmarks, PushUpDetector.LEFT_WRIST, 0.1, 0.9)
    res = detector.process(landmarks)
    assert detector.stage == "down"
    assert res["elbow_angle"] <= 90

    # Push back UP: Elbow back to > 160 degrees
    set_point(landmarks, PushUpDetector.LEFT_SHOULDER, 0.2, 0.5)
    set_point(landmarks, PushUpDetector.LEFT_ELBOW, 0.2, 0.7)
    set_point(landmarks, PushUpDetector.LEFT_WRIST, 0.2, 0.9)
    res = detector.process(landmarks)
    assert detector.stage == "up"
    assert res["reps"] == 1


def test_pushup_hip_sag():
    detector = PushUpDetector()
    landmarks = create_blank_landmarks()

    # Shoulder y=0.4, Ankle y=0.4 -> expected hip y=0.4
    # But Hip y=0.55 (sagging down by 0.15 > tolerance 0.08)
    set_point(landmarks, PushUpDetector.LEFT_SHOULDER, 0.2, 0.4)
    set_point(landmarks, PushUpDetector.LEFT_ELBOW, 0.2, 0.6)
    set_point(landmarks, PushUpDetector.LEFT_WRIST, 0.2, 0.8)
    set_point(landmarks, PushUpDetector.LEFT_HIP, 0.5, 0.55)
    set_point(landmarks, PushUpDetector.LEFT_ANKLE, 0.8, 0.4)
    set_point(landmarks, PushUpDetector.RIGHT_ELBOW, 0.2, 0.6, visibility=0.1)

    res = detector.process(landmarks)
    assert res["hip_status"] == "SAGGING"
