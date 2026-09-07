import math
import pytest
import sys
from pathlib import Path

# Add Main App to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "Main App"))

from core.base_exercise import BaseExercise


class ConcreteExercise(BaseExercise):
    def process(self, landmarks):
        return {}
    def reset(self):
        pass


def test_calculate_angle_right_angle():
    ex = ConcreteExercise()
    # (0, 1) -> (0, 0) -> (1, 0) : 90 degrees
    a = (0.0, 1.0)
    b = (0.0, 0.0)
    c = (1.0, 0.0)
    angle = ex.calculate_angle(a, b, c)
    assert abs(angle - 90.0) < 1e-4


def test_calculate_angle_straight_line():
    ex = ConcreteExercise()
    # (-1, 0) -> (0, 0) -> (1, 0) : 180 degrees
    a = (-1.0, 0.0)
    b = (0.0, 0.0)
    c = (1.0, 0.0)
    angle = ex.calculate_angle(a, b, c)
    assert abs(angle - 180.0) < 1e-4


def test_calculate_angle_zero_degrees():
    ex = ConcreteExercise()
    # (1, 0) -> (0, 0) -> (1, 0) : 0 degrees
    a = (1.0, 0.0)
    b = (0.0, 0.0)
    c = (1.0, 0.0)
    angle = ex.calculate_angle(a, b, c)
    assert abs(angle - 0.0) < 1e-4


def test_calculate_angle_45_degrees():
    ex = ConcreteExercise()
    # (1, 1) -> (0, 0) -> (1, 0) : 45 degrees
    a = (1.0, 1.0)
    b = (0.0, 0.0)
    c = (1.0, 0.0)
    angle = ex.calculate_angle(a, b, c)
    assert abs(angle - 45.0) < 1e-4


def test_calculate_angle_degenerate_points():
    ex = ConcreteExercise()
    # b == a (zero length vector)
    a = (0.0, 0.0)
    b = (0.0, 0.0)
    c = (1.0, 0.0)
    angle = ex.calculate_angle(a, b, c)
    assert angle == 0.0
