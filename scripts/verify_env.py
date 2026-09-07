from pathlib import Path
import sys
import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision

def test_model():
    model_path = Path(__file__).resolve().parent.parent / "Main App" / "ml_models" / "pose_landmarker_full.task"
    print(f"Checking model at: {model_path}")
    assert model_path.exists(), f"Model not found at {model_path}"
    print(f"Model file size: {model_path.stat().st_size / (1024 * 1024):.2f} MB")
    
    base_options = python.BaseOptions(model_asset_path=str(model_path))
    options = vision.PoseLandmarkerOptions(
        base_options=base_options,
        running_mode=vision.RunningMode.IMAGE,
        min_pose_detection_confidence=0.7,
        min_pose_presence_confidence=0.7,
        min_tracking_confidence=0.7,
    )
    landmarker = vision.PoseLandmarker.create_from_options(options)
    print("SUCCESS: MediaPipe PoseLandmarker initialized cleanly with full model!")
    landmarker.close()

if __name__ == "__main__":
    test_model()
