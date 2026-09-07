import sys
from pathlib import Path
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "Main App"))

from detectors.biceps_curl import BicepsCurlDetector
from detectors.squat import SquatDetector
from detectors.pushup import PushUpDetector
from detectors.shoulder_press import ShoulderPressDetector
from detectors.lunges import LungesDetector
from tests.mock_landmarks import create_blank_landmarks, set_point


@pytest.mark.parametrize("detector_cls,angle_key,form_keys", [
    (BicepsCurlDetector, "elbow_angle", ["shoulder_status", "swing_status"]),
    (SquatDetector, "knee_angle", ["back_angle", "depth_status"]),
    (PushUpDetector, "elbow_angle", ["body_alignment", "hip_status"]),
    (ShoulderPressDetector, "elbow_angle", ["extension_status", "back_arch_status"]),
    (LungesDetector, "front_knee_angle", ["torso_angle", "balance_status"]),
])
def test_detector_contract_keys_and_reset(detector_cls, angle_key, form_keys):
    detector = detector_cls()
    landmarks = create_blank_landmarks()

    # Process blank landmarks
    result = detector.process(landmarks)
    assert isinstance(result, dict)
    assert "reps" in result
    assert "stage" in result
    assert angle_key in result
    for k in form_keys:
        assert k in result, f"Expected {k} in {detector_cls.__name__} output"

    # Verify reset behavior
    detector.reps = 15
    detector.stage = "up"
    detector.reset()
    assert detector.reps == 0
    assert detector.stage is None
