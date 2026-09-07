"""
Vision Pipeline Benchmark Script for Adhi's AI Gym Coach.
Measures real performance metrics across all 5 exercise detectors:
- Frame conversion time (BGR to RGB)
- MediaPipe PoseLandmarker inference time
- Biomechanical detector execution time
- OpenCV skeleton and HUD overlay drawing time
- Total latency per frame & achievable FPS
"""

import os
import sys
import time
import platform
from pathlib import Path
import numpy as np
import cv2
import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision

# Add Main App to sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR / "Main App"))

from detectors.biceps_curl import BicepsCurlDetector
from detectors.squat import SquatDetector
from detectors.pushup import PushUpDetector
from detectors.shoulder_press import ShoulderPressDetector
from detectors.lunges import LungesDetector
from services.config.workout_config import POSE_CONNECTIONS


def run_benchmark(num_frames: int = 100, width: int = 640, height: int = 480):
    print("=" * 65)
    print("ADHI'S AI GYM COACH — COMPUTER VISION PIPELINE BENCHMARK")
    print("=" * 65)
    
    cpu_info = platform.processor() or platform.machine()
    system_info = f"{platform.system()} {platform.release()} ({platform.architecture()[0]})"
    python_ver = platform.python_version()
    
    print(f"Platform:          {system_info}")
    print(f"Processor/CPU:     {cpu_info}")
    print(f"Python Version:    {python_ver}")
    print(f"Test Resolution:   {width}x{height} (Standard 480p WebRTC stream)")
    print(f"Benchmark Frames:  {num_frames}")
    print("-" * 65)

    model_path = BASE_DIR / "Main App" / "ml_models" / "pose_landmarker_full.task"
    if not model_path.exists():
        print(f"ERROR: Model not found at {model_path}")
        return

    # Initialize PoseLandmarker
    base_options = python.BaseOptions(model_asset_path=str(model_path))
    options = vision.PoseLandmarkerOptions(
        base_options=base_options,
        running_mode=vision.RunningMode.VIDEO,
        min_pose_detection_confidence=0.7,
        min_pose_presence_confidence=0.7,
        min_tracking_confidence=0.7,
        output_segmentation_masks=False
    )
    landmarker = vision.PoseLandmarker.create_from_options(options)

    detectors = {
        "Biceps Curls (Dumbbell)": BicepsCurlDetector(),
        "Squats": SquatDetector(),
        "Push-ups": PushUpDetector(),
        "Shoulder Press": ShoulderPressDetector(),
        "Lunges": LungesDetector(),
    }

    # Generate synthetic camera frame (RGB person-like background)
    dummy_frame = np.full((height, width, 3), 120, dtype=np.uint8)
    # Draw simple person outline to ensure non-empty contrast
    cv2.circle(dummy_frame, (width // 2, height // 4), 40, (200, 180, 160), -1)
    cv2.line(dummy_frame, (width // 2, height // 4), (width // 2, height * 3 // 4), (50, 50, 200), 10)

    results_table = []
    timestamp_ms = 1000

    for exercise_name, detector in detectors.items():
        detector.reset()
        t_conversion = []
        t_inference = []
        t_detector = []
        t_draw = []
        t_total = []

        for frame_idx in range(num_frames):
            start_total = time.perf_counter()

            # 1. Conversion
            start_conv = time.perf_counter()
            rgb_data = cv2.cvtColor(dummy_frame, cv2.COLOR_BGR2RGB)
            mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_data)
            end_conv = time.perf_counter()

            # 2. Pose Inference
            start_inf = time.perf_counter()
            timestamp_ms += 33
            result = landmarker.detect_for_video(mp_image, timestamp_ms)
            end_inf = time.perf_counter()

            # 3. Detector logic (use detected or mock landmarks to test full code path)
            start_det = time.perf_counter()
            if result.pose_landmarks:
                landmarks = result.pose_landmarks[0]
                metrics = detector.process(landmarks)
            else:
                # Mock 33 landmarks with normalized coords to guarantee detector code path is benchmarked
                class MockLM:
                    def __init__(self, x=0.5, y=0.5, v=0.9):
                        self.x, self.y, self.visibility = x, y, v
                mock_landmarks = [MockLM() for _ in range(33)]
                metrics = detector.process(mock_landmarks)
            end_det = time.perf_counter()

            # 4. Annotation / Drawing
            start_drw = time.perf_counter()
            annotated = dummy_frame.copy()
            for s_idx, e_idx in POSE_CONNECTIONS:
                cv2.line(annotated, (width // 3, height // 3), (width * 2 // 3, height * 2 // 3), (0, 255, 0), 4)
            cv2.putText(annotated, f"Reps: {metrics.get('reps', 0)}", (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
            end_drw = time.perf_counter()

            end_total = time.perf_counter()

            t_conversion.append((end_conv - start_conv) * 1000)
            t_inference.append((end_inf - start_inf) * 1000)
            t_detector.append((end_det - start_det) * 1000)
            t_draw.append((end_drw - start_drw) * 1000)
            t_total.append((end_total - start_total) * 1000)

        # Average metrics (discarding first 5 warmup frames)
        avg_conv = np.mean(t_conversion[5:])
        avg_inf = np.mean(t_inference[5:])
        avg_det = np.mean(t_detector[5:])
        avg_draw = np.mean(t_draw[5:])
        avg_total = np.mean(t_total[5:])
        fps = 1000.0 / avg_total if avg_total > 0 else 0

        results_table.append({
            "Exercise": exercise_name,
            "Conversion (ms)": f"{avg_conv:.2f}",
            "Inference (ms)": f"{avg_inf:.2f}",
            "Detector (ms)": f"{avg_det:.3f}",
            "Annotation (ms)": f"{avg_draw:.2f}",
            "Total Latency (ms)": f"{avg_total:.2f}",
            "Throughput (FPS)": f"{fps:.1f}"
        })

    # Print results summary
    print(f"{'Exercise':<25} | {'Conv':<7} | {'Infer':<7} | {'Detect':<7} | {'Draw':<7} | {'Total':<8} | {'FPS':<6}")
    print("-" * 78)
    for row in results_table:
        print(f"{row['Exercise']:<25} | {row['Conversion (ms)']:<7} | {row['Inference (ms)']:<7} | {row['Detector (ms)']:<7} | {row['Annotation (ms)']:<7} | {row['Total Latency (ms)']:<8} | {row['Throughput (FPS)']:<6}")
    print("=" * 78)

    landmarker.close()
    return results_table, {
        "platform": system_info,
        "cpu": cpu_info,
        "python": python_ver,
        "resolution": f"{width}x{height}",
        "frames": num_frames
    }


if __name__ == "__main__":
    run_benchmark(num_frames=50)
