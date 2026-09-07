import sys
from pathlib import Path
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "Main App"))

from services.coaching.llm import LLMCoach


def test_coach_fallback_when_client_none():
    coach = LLMCoach(groq_client=None)
    
    # Test event fallbacks
    fb = coach.give_feedback("workout_started", None)
    assert "Workout started" in fb

    fb = coach.give_feedback("workout_completed", None)
    assert "completed your workout" in fb

    fb = coach.give_feedback("no_pose_detected", None)
    assert "camera" in fb.lower()


def test_coach_fallback_on_form_issues():
    coach = LLMCoach(groq_client=None)

    fb = coach.give_feedback("ongoing_form_check", "Elbow drifting forward")
    assert "elbow" in fb.lower()

    fb = coach.give_feedback("ongoing_form_check", "Torso swinging")
    assert "swing" in fb.lower() or "brace" in fb.lower()

    fb = coach.give_feedback("ongoing_form_check", "Hip sagging")
    assert "hip" in fb.lower() or "straight line" in fb.lower()
