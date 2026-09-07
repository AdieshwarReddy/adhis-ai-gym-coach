import sys
from pathlib import Path
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "Main App"))

from detectors.biceps_curl import BicepsCurlDetector
from tests.mock_landmarks import create_blank_landmarks, set_point


def test_biceps_curl_rep_cycle():
    detector = BicepsCurlDetector()
    landmarks = create_blank_landmarks()

    # Setup Left side: Shoulder 11, Elbow 13, Wrist 15
    # Down position (angle ~ 180 degrees)
    set_point(landmarks, BicepsCurlDetector.LEFT_SHOULDER, 0.5, 0.2)
    set_point(landmarks, BicepsCurlDetector.LEFT_ELBOW, 0.5, 0.5)
    set_point(landmarks, BicepsCurlDetector.LEFT_WRIST, 0.5, 0.8)
    set_point(landmarks, BicepsCurlDetector.LEFT_HIP, 0.5, 0.6)
    set_point(landmarks, BicepsCurlDetector.RIGHT_HIP, 0.5, 0.6)
    set_point(landmarks, BicepsCurlDetector.RIGHT_SHOULDER, 0.5, 0.2)

    res = detector.process(landmarks)
    assert res["reps"] == 0
    assert res["elbow_angle"] >= 160
    assert res["shoulder_status"] == "STABLE"

    # Curl UP (angle < 50 degrees)
    # Shoulder=(0.5, 0.2), Elbow=(0.5, 0.5), Wrist=(0.48, 0.22)
    set_point(landmarks, BicepsCurlDetector.LEFT_WRIST, 0.48, 0.22)
    res = detector.process(landmarks)
    assert res["reps"] == 0
    assert detector.stage == "up"
    assert res["elbow_angle"] < 50

    # Return DOWN (angle > 160 degrees)
    set_point(landmarks, BicepsCurlDetector.LEFT_WRIST, 0.5, 0.8)
    res = detector.process(landmarks)
    assert res["reps"] == 1
    assert detector.stage == "down"
    assert res["elbow_angle"] >= 160


def test_biceps_curl_low_visibility_suppression():
    detector = BicepsCurlDetector()
    landmarks = create_blank_landmarks()

    # Left arm with low visibility elbow
    set_point(landmarks, BicepsCurlDetector.LEFT_SHOULDER, 0.5, 0.2, visibility=0.9)
    set_point(landmarks, BicepsCurlDetector.LEFT_ELBOW, 0.5, 0.5, visibility=0.4) # Below 0.7
    set_point(landmarks, BicepsCurlDetector.LEFT_WRIST, 0.48, 0.22, visibility=0.9)
    set_point(landmarks, BicepsCurlDetector.RIGHT_ELBOW, 0.5, 0.5, visibility=0.1)

    res = detector.process(landmarks)
    # Stage should NOT transition to "up" because visibility is low
    assert detector.stage is None
    assert res["reps"] == 0


def test_biceps_curl_elbow_drift_detection():
    detector = BicepsCurlDetector()
    landmarks = create_blank_landmarks()

    # Shoulder at x=0.5, Elbow drifted forward to x=0.60 (drift 0.10 > tolerance 0.06)
    set_point(landmarks, BicepsCurlDetector.LEFT_SHOULDER, 0.5, 0.2)
    set_point(landmarks, BicepsCurlDetector.LEFT_ELBOW, 0.60, 0.5)
    set_point(landmarks, BicepsCurlDetector.LEFT_WRIST, 0.58, 0.25)
    set_point(landmarks, BicepsCurlDetector.RIGHT_ELBOW, 0.5, 0.5, visibility=0.1)

    res = detector.process(landmarks)
    assert res["shoulder_status"] == "ELBOW DRIFTING"


def test_biceps_curl_reset():
    detector = BicepsCurlDetector()
    detector.reps = 10
    detector.stage = "up"
    detector.reset()
    assert detector.reps == 0
    assert detector.stage is None
