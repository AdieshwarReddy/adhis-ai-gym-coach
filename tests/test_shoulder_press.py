import sys
from pathlib import Path
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "Main App"))

from detectors.shoulder_press import ShoulderPressDetector
from tests.mock_landmarks import create_blank_landmarks, set_point


def test_shoulder_press_rep_cycle():
    detector = ShoulderPressDetector()
    landmarks = create_blank_landmarks()

    # Start position: Dumbbells at shoulders, elbows bent (~70 degrees)
    # Shoulder=(0.5, 0.3), Elbow=(0.6, 0.4), Wrist=(0.55, 0.3)
    set_point(landmarks, ShoulderPressDetector.LEFT_SHOULDER, 0.5, 0.3)
    set_point(landmarks, ShoulderPressDetector.LEFT_ELBOW, 0.6, 0.4)
    set_point(landmarks, ShoulderPressDetector.LEFT_WRIST, 0.55, 0.3)
    set_point(landmarks, ShoulderPressDetector.LEFT_HIP, 0.5, 0.6)
    set_point(landmarks, ShoulderPressDetector.LEFT_KNEE, 0.5, 0.8)
    set_point(landmarks, ShoulderPressDetector.RIGHT_ELBOW, 0.6, 0.4, visibility=0.1)

    res = detector.process(landmarks)
    assert res["reps"] == 0
    assert res["elbow_angle"] < 90

    # Press overhead: Arm extended straight up (> 160 degrees)
    # Shoulder=(0.5, 0.4), Elbow=(0.5, 0.25), Wrist=(0.5, 0.1) -> 180 degrees
    set_point(landmarks, ShoulderPressDetector.LEFT_SHOULDER, 0.5, 0.4)
    set_point(landmarks, ShoulderPressDetector.LEFT_ELBOW, 0.5, 0.25)
    set_point(landmarks, ShoulderPressDetector.LEFT_WRIST, 0.5, 0.1)
    res = detector.process(landmarks)
    assert res["reps"] == 0
    assert detector.stage == "up"
    assert res["elbow_angle"] > 160
    assert res["extension_status"] == "FULL EXTENSION"

    # Lower back to shoulders: Elbow angle < 90 degrees
    set_point(landmarks, ShoulderPressDetector.LEFT_SHOULDER, 0.5, 0.3)
    set_point(landmarks, ShoulderPressDetector.LEFT_ELBOW, 0.6, 0.4)
    set_point(landmarks, ShoulderPressDetector.LEFT_WRIST, 0.55, 0.3)
    res = detector.process(landmarks)
    assert res["reps"] == 1
    assert detector.stage == "down"


def test_shoulder_press_excessive_arch():
    detector = ShoulderPressDetector()
    landmarks = create_blank_landmarks()

    # Shoulder=(0.3, 0.3), Hip=(0.5, 0.6), Knee=(0.5, 0.8) -> leaning back severely
    set_point(landmarks, ShoulderPressDetector.LEFT_SHOULDER, 0.3, 0.3)
    set_point(landmarks, ShoulderPressDetector.LEFT_ELBOW, 0.3, 0.2)
    set_point(landmarks, ShoulderPressDetector.LEFT_WRIST, 0.3, 0.1)
    set_point(landmarks, ShoulderPressDetector.LEFT_HIP, 0.5, 0.6)
    set_point(landmarks, ShoulderPressDetector.LEFT_KNEE, 0.5, 0.8)
    set_point(landmarks, ShoulderPressDetector.RIGHT_ELBOW, 0.3, 0.2, visibility=0.1)

    res = detector.process(landmarks)
    assert res["back_arch_status"] in ("Slight Arch", "Excessive Arch")
