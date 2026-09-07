import sys
from pathlib import Path
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "Main App"))

from detectors.lunges import LungesDetector
from tests.mock_landmarks import create_blank_landmarks, set_point


def test_lunges_rep_cycle():
    detector = LungesDetector()
    landmarks = create_blank_landmarks()

    # Standing: Both legs straight
    set_point(landmarks, LungesDetector.LEFT_HIP, 0.45, 0.5)
    set_point(landmarks, LungesDetector.LEFT_KNEE, 0.45, 0.7)
    set_point(landmarks, LungesDetector.LEFT_ANKLE, 0.45, 0.9)
    set_point(landmarks, LungesDetector.RIGHT_HIP, 0.55, 0.5)
    set_point(landmarks, LungesDetector.RIGHT_KNEE, 0.55, 0.7)
    set_point(landmarks, LungesDetector.RIGHT_ANKLE, 0.55, 0.9)
    set_point(landmarks, LungesDetector.LEFT_SHOULDER, 0.45, 0.2)
    set_point(landmarks, LungesDetector.RIGHT_SHOULDER, 0.55, 0.2)

    res = detector.process(landmarks)
    assert res["reps"] == 0
    assert res["balance_status"] == "BALANCED"

    # Lunge DOWN with Left leg: Left Knee bent to 90 degrees (< 100)
    # Hip=(0.4, 0.65), Knee=(0.45, 0.65), Ankle=(0.45, 0.85)
    set_point(landmarks, LungesDetector.LEFT_HIP, 0.35, 0.65)
    set_point(landmarks, LungesDetector.LEFT_KNEE, 0.45, 0.65)
    set_point(landmarks, LungesDetector.LEFT_ANKLE, 0.45, 0.85)
    res = detector.process(landmarks)
    assert detector.stage == "down"
    assert res["reps"] == 0
    assert res["front_knee_angle"] < 100

    # Stand back UP: Left Knee angle returns to > 160 degrees
    set_point(landmarks, LungesDetector.LEFT_HIP, 0.45, 0.5)
    set_point(landmarks, LungesDetector.LEFT_KNEE, 0.45, 0.7)
    set_point(landmarks, LungesDetector.LEFT_ANKLE, 0.45, 0.9)
    res = detector.process(landmarks)
    assert detector.stage == "up"
    assert res["reps"] == 1


def test_lunges_off_balance():
    detector = LungesDetector()
    landmarks = create_blank_landmarks()

    # Torso shifted far right (shoulders around 0.7, hips around 0.5 -> offset 0.2 > 0.10)
    set_point(landmarks, LungesDetector.LEFT_SHOULDER, 0.65, 0.2)
    set_point(landmarks, LungesDetector.RIGHT_SHOULDER, 0.75, 0.2)
    set_point(landmarks, LungesDetector.LEFT_HIP, 0.45, 0.5)
    set_point(landmarks, LungesDetector.RIGHT_HIP, 0.55, 0.5)
    set_point(landmarks, LungesDetector.LEFT_KNEE, 0.45, 0.7)
    set_point(landmarks, LungesDetector.LEFT_ANKLE, 0.45, 0.9)
    set_point(landmarks, LungesDetector.RIGHT_KNEE, 0.55, 0.7)
    set_point(landmarks, LungesDetector.RIGHT_ANKLE, 0.55, 0.9)

    res = detector.process(landmarks)
    assert res["balance_status"] == "OFF BALANCE"
