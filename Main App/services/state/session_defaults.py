import streamlit as st


def initial_session_defaults():
    defaults = {
        "reps": 0,
        "target_sets": 0,
        "reps_per_set": 0,
        "sets_completed": 0,
        "current_set_reps": 0,
        "workout_complete": False,
        "last_notified_sets_completed": 0,
        "last_notified_workout_complete": False,
        "last_saved_sets_completed": 0,
        "set_cycle_started_at": 0.0,
        "last_exercise_type": "Squats",

        # Workout plan (set before starting)
        "workout_started": False,
        "plan_exercise": "Squats",
        "plan_sets": 3,
        "plan_reps": 10,

        # Cloud session tracking
        "workout_session_id": None,
        "last_coach_summary": "",

        # Chat history for Ask Adhi Coach
        "chat_history": [],

        # User account info
        "user_email": "",
        "is_cloud_user": False,

        # New mode selection and rest timer
        "workout_mode": "Standard Sets",  # or "HIIT / Interval"
        "rest_duration": 45,  # seconds for standard mode
        "is_resting": False,
        "rest_start_time": 0.0,
        "rest_end_time": 0.0,
        # HIIT specific
        "hiit_work_duration": 30,
        "hiit_rest_duration": 15,
        "hiit_total_rounds": 5,
        "hiit_current_round": 0,
        "hiit_phase": "WORK",  # or "REST"
        "hiit_phase_end_time": 0.0,
        "hiit_round_reps": [],

        # Common Angles
        "knee_angle": 0,
        "back_angle": 0,
        "elbow_angle": 0,
        "front_knee_angle": 0,
        "torso_angle": 0,

        # Status fields
        "depth_status": "N/A",
        "body_alignment": "N/A",
        "hip_status": "N/A",
        "shoulder_status": "N/A",
        "swing_status": "N/A",
        "extension_status": "N/A",
        "back_arch_status": "N/A",
        "balance_status": "N/A",
    }

    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value
