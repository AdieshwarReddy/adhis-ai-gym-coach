from dataclasses import dataclass
from typing import List


@dataclass
class MockLandmark:
    x: float = 0.5
    y: float = 0.5
    z: float = 0.0
    visibility: float = 0.99


def create_blank_landmarks(count: int = 33, visibility: float = 0.95) -> List[MockLandmark]:
    return [MockLandmark(x=0.5, y=0.5, z=0.0, visibility=visibility) for _ in range(count)]


def set_point(landmarks: List[MockLandmark], idx: int, x: float, y: float, visibility: float = 0.95):
    landmarks[idx] = MockLandmark(x=x, y=y, z=0.0, visibility=visibility)
