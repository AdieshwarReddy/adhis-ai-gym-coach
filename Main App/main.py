import streamlit as st
import os
import time
import math
import pandas as pd
from pathlib import Path

# Load .env file into os.environ automatically (runs before anything else)
try:
    from dotenv import load_dotenv
    _env_path = Path(__file__).resolve().parent.parent / ".env"
    if _env_path.exists():
        load_dotenv(dotenv_path=_env_path, override=False)
except ImportError:
    pass

import sys
_APP_DIR = Path(__file__).resolve().parent
if str(_APP_DIR) not in sys.path:
    sys.path.insert(0, str(_APP_DIR))

from services.auth.login_wall import render_login_wall
from services.state.session_defaults import initial_session_defaults
from services.config.workout_config import EXERCISE_OPTIONS
from services.ui.style_loader import load_css, inject_local_font, inject_webrtc_styles
from services.persistence.exercise_repository import (
    init_db, get_users_exercises, add_exercise, get_user_stats,
    create_workout_session, complete_workout_session,
    log_form_event, get_form_events_for_session, save_workout_summary,
    create_cardio_session, add_cardio_route_point, complete_cardio_session,
    get_user_cardio_sessions, get_cardio_route_points, delete_cardio_session,
    save_transformation_record, get_transformation_records
)
from services.cardio.tracker import CardioTracker
from services.cardio.geolocation import format_duration
from services.cardio.geolocation_component import render_gps_collector
from services.maps.map_view import render_map_component
from streamlit_webrtc import webrtc_streamer, WebRtcMode
from services.vision.exercise_video_processor import VideoProcessorClass
from services.tracking.metrics import sync_metrics_update
from groq import Groq
from services.coaching.llm import LLMCoach
from services.coaching.tts import TextToSpeech
from services.coaching.voice_pipeline import VoicePipeline, autoplay_audio


# ─────────────────────────────────────────────────────────────────────────────
# PAGE CONFIG
# ─────────────────────────────────────────────────────────────────────────────
def main():
    st.set_page_config(
        page_icon="🏋️‍♀️",
        page_title="Adhi's AI Gym Coach",
        initial_sidebar_state="expanded",
        layout="wide"
    )

    _STATIC_DIR = Path(__file__).resolve().parent / "static"
    load_css(str(_STATIC_DIR / "style.css"))
    inject_local_font(str(_STATIC_DIR / "AdobeClean.otf"), "AdobeClean")

    init_db()

    # ── Auth Gate ────────────────────────────────────────────────────────────
    if not render_login_wall():
        return

    initial_session_defaults()

    # ── Voice/LLM pipeline init (Supports Groq + Google Gemini) ─────────────
    if "voice_pipeline" not in st.session_state:
        try:
            groq_key = os.environ.get("GROQ_API_KEY", "")
            gemini_key = os.environ.get("GEMINI_API_KEY", "")
            try:
                if not groq_key and hasattr(st, "secrets") and "GROQ_API_KEY" in st.secrets:
                    groq_key = st.secrets["GROQ_API_KEY"]
                if not gemini_key and hasattr(st, "secrets") and "GEMINI_API_KEY" in st.secrets:
                    gemini_key = st.secrets["GEMINI_API_KEY"]
            except Exception:
                pass
            groq_client = Groq(api_key=groq_key) if groq_key else None
            llm_coach = LLMCoach(groq_client=groq_client, gemini_api_key=gemini_key)
            tts = TextToSpeech()
            st.session_state.voice_pipeline = VoicePipeline(llm_coach, tts)
        except Exception:
            st.session_state.voice_pipeline = None


    # ── Navigation ───────────────────────────────────────────────────────────
    with st.sidebar:
        st.markdown(
            "<div style='padding:0.5rem 0 1.5rem 0;'>"
            "<span style='font-size:1.4rem; font-weight:700; letter-spacing:0.05em;'>🏋️‍♂️ ADHI'S<br>"
            "<span style='color:#0ecfb5;'>AI GYM COACH</span></span></div>",
            unsafe_allow_html=True
        )

        username = st.session_state.get("username", "")
        if username:
            st.caption(f"👤 {username}")

        st.divider()

        NAV_PAGES = [
            "🏠 Dashboard",
            "🏋️ Strength Workout",
            "🏃 Run / Cardio",
            "📸 Results & Transformation",
            "📋 History",
            "📊 Analytics",
            "🤖 Ask Adhi Coach",
            "👤 Profile"
        ]

        if "current_page" not in st.session_state:
            st.session_state["current_page"] = "🏠 Dashboard"

        current_val = st.session_state.get("current_page", "🏠 Dashboard")
        default_idx = NAV_PAGES.index(current_val) if current_val in NAV_PAGES else 0

        # Handle programmatic redirection before radio is rendered
        if st.session_state.get("redirect_page"):
            redirect_target = st.session_state.pop("redirect_page")
            if redirect_target in NAV_PAGES:
                default_idx = NAV_PAGES.index(redirect_target)
                st.session_state["nav_selection"] = redirect_target
                st.session_state["current_page"] = redirect_target

        if "nav_selection" not in st.session_state:
            st.session_state["nav_selection"] = NAV_PAGES[default_idx]

        page = st.radio(
            "Navigate",
            NAV_PAGES,
            index=default_idx,
            label_visibility="collapsed",
            key="nav_selection",
        )
        st.session_state["current_page"] = page

        st.divider()

        if st.button("🚪 Sign Out", width='stretch'):
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            st.rerun()

    # ── Page router ──────────────────────────────────────────────────────────
    if page == "🏠 Dashboard":
        _render_dashboard()
    elif page == "🏋️ Strength Workout":
        _render_workout_page()
    elif page == "🏃 Run / Cardio":
        _render_cardio_page()
    elif page == "📸 Results & Transformation":
        _render_results_page()
    elif page == "📋 History":
        _render_history()
    elif page == "📊 Analytics":
        _render_analytics()
    elif page == "🤖 Ask Adhi Coach":
        _render_chatbot()
    elif page == "👤 Profile":
        _render_profile()


# ─────────────────────────────────────────────────────────────────────────────
# DASHBOARD
# ─────────────────────────────────────────────────────────────────────────────
def _render_dashboard():
    user_id = st.session_state.get("user_id", "")
    username = st.session_state.get("username", "Athlete")

    # Show "Welcome" on first ever signup, "Welcome back" on every subsequent login
    is_new = st.session_state.pop("is_new_user", False)

    if is_new:
        st.markdown(f"## 🎉 Welcome, **{username}**!")
        st.markdown(
            "Your account is set up and ready to go. "
            "Start with a **Strength Workout** or a **Run** below, or explore the sidebar to discover all features."
        )
        st.info(
            "💡 **Quick start tip:** Head to **🏋️ Strength Workout** to let the AI count your reps with live pose tracking, "
            "or tap **🏃 Run / Cardio** to start GPS-tracked outdoor training."
        )
    else:
        st.markdown(f"## 👋 Welcome back, **{username}**!")
        st.markdown("Track your form, count your reps, track your runs, and let AI coach you to peak performance.")

    st.divider()

    stats = get_user_stats(str(user_id))
    mins, secs = divmod(stats["total_time_sec"], 60)

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.metric("🏋️ Workouts", stats["total_workouts"])
    with c2:
        st.metric("🔁 Total Reps", f"{stats['total_reps']:,}")
    with c3:
        st.metric("🏃 Cardio Dist", f"{stats.get('total_cardio_distance_km', 0.0)} km")
    with c4:
        st.metric("⏱️ Active Time", f"{mins}m {secs}s")

    st.divider()
    st.markdown("### 🎯 Start Activity")

    col_act1, col_act2 = st.columns(2)
    with col_act1:
        st.markdown(
            """
            <div style="background:#111520; border:1px solid rgba(14,207,181,0.3); border-radius:10px; padding:16px; margin-bottom:12px;">
                <h3 style="margin:0 0 8px 0; color:#0ecfb5;">🏋️ STRENGTH WORKOUT</h3>
                <p style="color:#9ca3af; font-size:13px; margin:0 0 12px 0;">
                    Real-time MediaPipe pose tracking, automated rep counting, form analysis & voice coaching.
                </p>
            </div>
            """,
            unsafe_allow_html=True
        )
        if st.button("Start Strength Workout →", width="stretch", type="primary", key="dash_start_strength"):
            st.session_state.redirect_page = "🏋️ Strength Workout"
            st.rerun()

    with col_act2:
        st.markdown(
            """
            <div style="background:#111520; border:1px solid rgba(59,130,246,0.3); border-radius:10px; padding:16px; margin-bottom:12px;">
                <h3 style="margin:0 0 8px 0; color:#3b82f6;">🏃 RUN / WALK</h3>
                <p style="color:#9ca3af; font-size:13px; margin:0 0 12px 0;">
                    High-accuracy GPS route tracking, live pace, speed, geodesic distance & route replay.
                </p>
            </div>
            """,
            unsafe_allow_html=True
        )
        if st.button("Start Run / Walk →", width="stretch", type="secondary", key="dash_start_cardio"):
            st.session_state.redirect_page = "🏃 Run / Cardio"
            st.rerun()

    st.markdown("<div style='margin-top:12px;'></div>", unsafe_allow_html=True)
    c_btn1, c_btn2, c_btn3 = st.columns(3)
    with c_btn1:
        if st.button("📸 View Before & After", width='stretch', key="dash_btn_results"):
            st.session_state.redirect_page = "📸 Results & Transformation"
            st.rerun()
    with c_btn2:
        if st.button("📊 View Progress", width='stretch', key="dash_btn_progress"):
            st.session_state.redirect_page = "📊 Analytics"
            st.rerun()
    with c_btn3:
        if st.button("🤖 Ask Adhi Coach", width='stretch', key="dash_btn_coach"):
            st.session_state.redirect_page = "🤖 Ask Adhi Coach"
            st.rerun()

    # Recent activity
    st.divider()
    st.markdown("### 📋 Recent Activity")
    exercises = get_users_exercises(str(user_id))
    cardio_sessions = get_user_cardio_sessions(str(user_id))

    rows = []
    for r in (exercises or [])[:6]:
        rows.append({
            "Date": str(r.get("created_at", ""))[:10],
            "Type": "Strength",
            "Activity": r.get("exercise_name", ""),
            "Metric": f"{r.get('reps', 0)} reps ({r.get('sets', 1)} sets)"
        })
    for c in (cardio_sessions or [])[:6]:
        dist_km = round(c.get("distance_meters", 0.0) / 1000.0, 2)
        dur = format_duration(c.get("moving_seconds", 0))
        rows.append({
            "Date": str(c.get("started_at", ""))[:10],
            "Type": "Cardio",
            "Activity": c.get("activity_type", "Running"),
            "Metric": f"{dist_km} km ({dur})"
        })

    if rows:
        df = pd.DataFrame(rows)
        df.sort_values(by="Date", ascending=False, inplace=True)
        df.reset_index(drop=True, inplace=True)
        df.index += 1
        st.dataframe(df, use_container_width=True)
    else:
        st.info("No workouts logged yet. Select an activity above to begin! 💪")


def _start_strength_workout(exercise: str, sets: int, reps: int):
    """Initializes and starts a strength workout session."""
    st.session_state.exercise_type = exercise
    st.session_state.target_sets = int(sets)
    st.session_state.reps_per_set = int(reps)
    st.session_state.reps = 0
    st.session_state.current_set_reps = 0
    st.session_state.sets_completed = 0
    st.session_state.workout_started = True
    st.session_state.reset_requested = True
    st.session_state.set_cycle_started_at = time.time()
    st.session_state.last_saved_sets_completed = 0
    st.session_state.workout_session_id = create_workout_session(str(st.session_state.get("user_id", "")))

    if st.session_state.get("voice_pipeline"):
        result = st.session_state.voice_pipeline.process_event(
            event="workout_started", exercise=exercise, metrics={}
        )
        if result:
            st.session_state.audio_to_play, st.session_state.coach_feedback = result

    st.session_state.last_notified_sets_completed = 0
    st.session_state.last_notified_workout_complete = False


def _end_strength_workout():
    """Concludes the active strength workout and saves summaries."""
    exercise = st.session_state.get("exercise_type", "Workout")
    session_id = st.session_state.get("workout_session_id")
    duration = int(time.time() - st.session_state.get("set_cycle_started_at", time.time()))
    if session_id:
        complete_workout_session(session_id, duration)
        total_reps = st.session_state.get("reps", 0)
        completed_sets = st.session_state.get("sets_completed", 0)
        summary_text = _generate_workout_summary(exercise, completed_sets, total_reps, duration)
        save_workout_summary(session_id, total_reps, completed_sets, duration, summary_text)
        st.session_state.last_coach_summary = summary_text

    st.session_state.workout_started = False
    if st.session_state.get("voice_pipeline"):
        result = st.session_state.voice_pipeline.process_event(
            event="workout_completed", exercise=exercise, metrics={}
        )
        if result:
            st.session_state.audio_to_play, st.session_state.coach_feedback = result


# ─────────────────────────────────────────────────────────────────────────────
# WORKOUT PAGE (Strength: MediaPipe + Live Camera)
# ─────────────────────────────────────────────────────────────────────────────
def _render_workout_page():
    workout_started = st.session_state.get("workout_started", False)

    with st.sidebar:
        st.subheader("Workout Plan")

        if not workout_started:
            plan_exercise = st.selectbox("Exercise", options=EXERCISE_OPTIONS, key="plan_exercise")
            plan_sets = st.number_input("Sets", min_value=1, max_value=50, key="plan_sets", step=1, value=3)
            plan_reps = st.number_input("Reps per Set", min_value=1, max_value=50, key="plan_reps", step=1, value=10)
            st.markdown("")
            if st.button("▶ Start Workout", width="stretch", type="primary", key="start_session_button"):
                _start_strength_workout(plan_exercise, plan_sets, plan_reps)
                st.rerun()
        else:
            exercise = st.session_state.get("exercise_type")
            sets = st.session_state.get("target_sets")
            reps = st.session_state.get("reps_per_set")
            st.info(f"**{exercise}** — {sets} × {reps} reps")

            if st.button("⏹ End Workout", key="end_session_button", width="stretch"):
                _end_strength_workout()
                st.rerun()

        # Live metrics in sidebar during workout
        if workout_started:
            st.divider()
            st.subheader("📊 Live Progress")
            total_reps = st.session_state.get("reps", 0)
            current_set_reps = st.session_state.get("current_set_reps", 0)
            reps_per_set = st.session_state.get("reps_per_set", 0)
            sets_completed = st.session_state.get("sets_completed", 0)
            target_sets = st.session_state.get("target_sets", 0)
            st.metric("Total Reps", f"{total_reps}")
            st.metric("Set Reps", f"{current_set_reps} / {reps_per_set}")
            st.metric("Sets Done", f"{sets_completed} / {target_sets}")

            exercise = st.session_state.get("exercise_type")
            st.divider()
            _render_sidebar_form_metrics(exercise)

    # Main area
    st.title("🏋️‍♂️ Strength Workout")
    st.caption("Real-time pose detection · Automated rep counting · Live form analysis & voice coaching")

    if st.session_state.get("audio_to_play"):
        autoplay_audio(st.session_state.audio_to_play)

    if st.session_state.get("coach_feedback"):
        st.success(f"🤖 **Coach:** {st.session_state.coach_feedback}")

    if st.session_state.get("last_coach_summary"):
        with st.expander("📝 Session Summary", expanded=True):
            st.info(st.session_state.last_coach_summary)
        st.session_state.last_coach_summary = ""

    if not workout_started:
        st.markdown(
            """
            <div style="background:#111520; border:1px solid rgba(14,207,181,0.35); border-radius:12px; padding:20px 24px; margin-bottom:20px;">
                <h3 style="margin:0 0 6px 0; color:#0ecfb5;">🎯 Configure Your Strength Workout</h3>
                <p style="color:#9ca3af; font-size:13px; margin:0;">
                    Select your target exercise and set/rep goals below, then click <b>START WORKOUT & CAMERA</b> to begin.
                </p>
            </div>
            """,
            unsafe_allow_html=True
        )

        col_cfg1, col_cfg2, col_cfg3 = st.columns([2, 1, 1])
        with col_cfg1:
            main_exercise = st.selectbox("Select Exercise", options=EXERCISE_OPTIONS, key="main_cfg_exercise")
        with col_cfg2:
            main_sets = st.number_input("Target Sets", min_value=1, max_value=50, value=3, step=1, key="main_cfg_sets")
        with col_cfg3:
            main_reps = st.number_input("Reps / Set", min_value=1, max_value=50, value=10, step=1, key="main_cfg_reps")

        st.markdown("<div style='margin-top:8px;'></div>", unsafe_allow_html=True)
        if st.button("▶ START WORKOUT & CAMERA", width="stretch", type="primary", key="main_start_workout_btn"):
            _start_strength_workout(main_exercise, main_sets, main_reps)
            st.rerun()

        # Exercise Guide Preview Cards
        st.divider()
        st.markdown("### 💡 Supported Exercise Biomechanics")
        g1, g2, g3 = st.columns(3)
        with g1:
            st.markdown(
                """
                <div style="background:#111520; border:1px solid #2d3348; border-radius:8px; padding:12px 16px;">
                    <b style="color:#fff;">🏋️ Squats</b><br>
                    <span style="color:#9ca3af; font-size:12px;">Tracks knee flexion depth & torso back lean angle.</span>
                </div>
                """,
                unsafe_allow_html=True
            )
        with g2:
            st.markdown(
                """
                <div style="background:#111520; border:1px solid #2d3348; border-radius:8px; padding:12px 16px;">
                    <b style="color:#fff;">💪 Biceps Curls</b><br>
                    <span style="color:#9ca3af; font-size:12px;">Monitors elbow flexion, elbow drift & torso swinging.</span>
                </div>
                """,
                unsafe_allow_html=True
            )
        with g3:
            st.markdown(
                """
                <div style="background:#111520; border:1px solid #2d3348; border-radius:8px; padding:12px 16px;">
                    <b style="color:#fff;">🤸 Push-ups & Lunges</b><br>
                    <span style="color:#9ca3af; font-size:12px;">Verifies body collinearity, hip sag/pike & bilateral depth.</span>
                </div>
                """,
                unsafe_allow_html=True
            )

    else:
        # Live HUD status banner
        exercise = st.session_state.get("exercise_type", "")
        total_reps = st.session_state.get("reps", 0)
        current_set_reps = st.session_state.get("current_set_reps", 0)
        reps_per_set = st.session_state.get("reps_per_set", 10)
        sets_completed = st.session_state.get("sets_completed", 0)
        target_sets = st.session_state.get("target_sets", 3)

        st.markdown(
            f"""
            <div style="background:#111520; border:1px solid #0ecfb5; border-radius:12px; padding:14px 20px; margin-bottom:16px;">
                <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:10px;">
                    <div>
                        <span style="font-size:12px; color:#9ca3af; text-transform:uppercase;">ACTIVE EXERCISE</span>
                        <div style="font-size:1.4rem; font-weight:800; color:#0ecfb5;">{exercise}</div>
                    </div>
                    <div style="display:flex; gap:20px;">
                        <div>
                            <span style="font-size:11px; color:#9ca3af;">TOTAL REPS</span>
                            <div style="font-size:1.4rem; font-weight:800; color:#fff;">{total_reps}</div>
                        </div>
                        <div>
                            <span style="font-size:11px; color:#9ca3af;">CURRENT SET</span>
                            <div style="font-size:1.4rem; font-weight:800; color:#0ecfb5;">{current_set_reps} / {reps_per_set}</div>
                        </div>
                        <div>
                            <span style="font-size:11px; color:#9ca3af;">SETS DONE</span>
                            <div style="font-size:1.4rem; font-weight:800; color:#fff;">{sets_completed} / {target_sets}</div>
                        </div>
                    </div>
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )

        context = webrtc_streamer(
            key="exercise-analysis",
            mode=WebRtcMode.SENDRECV,
            video_processor_factory=VideoProcessorClass,
            rtc_configuration={"iceServers": [{"urls": ["stun:stun.l.google.com:19302"]}]},
            media_stream_constraints={"video": True, "audio": False},
            async_processing=True
        )

        sync_metrics_update(context)
        _maybe_log_form_events()

        if context.state.playing:
            time.sleep(0.25)
            st.rerun()

        inject_webrtc_styles()

        st.markdown("<div style='margin-top:16px;'></div>", unsafe_allow_html=True)
        if st.button("⏹ END WORKOUT & SAVE", width="stretch", type="secondary", key="main_end_workout_btn"):
            _end_strength_workout()
            st.rerun()


def _render_sidebar_form_metrics(exercise):
    if exercise == "Squats":
        st.subheader("📐 Squat Metrics")
        st.metric("Knee Angle", f"{st.session_state.knee_angle}°")
        st.metric("Back Angle", f"{st.session_state.back_angle}°")
        st.metric("Depth", st.session_state.depth_status)
    elif exercise == "Push-ups":
        st.subheader("📐 Push-up Metrics")
        st.metric("Elbow Angle", f"{st.session_state.elbow_angle}°")
        st.metric("Body Line", st.session_state.body_alignment)
        st.metric("Hip", st.session_state.hip_status)
    elif exercise == "Biceps Curls (Dumbbell)":
        st.subheader("📐 Curl Metrics")
        st.metric("Elbow Angle", f"{st.session_state.elbow_angle}°")
        st.metric("Elbow Stability", st.session_state.shoulder_status)
        st.metric("Swing", st.session_state.swing_status)
    elif exercise == "Shoulder Press":
        st.subheader("📐 Press Metrics")
        st.metric("Elbow Angle", f"{st.session_state.elbow_angle}°")
        st.metric("Extension", st.session_state.extension_status)
        st.metric("Back Arch", st.session_state.back_arch_status)
    elif exercise == "Lunges":
        st.subheader("📐 Lunge Metrics")
        st.metric("Knee Angle", f"{st.session_state.front_knee_angle}°")
        st.metric("Torso Angle", f"{st.session_state.torso_angle}°")
        st.metric("Balance", st.session_state.balance_status)


def _maybe_log_form_events():
    session_id = st.session_state.get("workout_session_id")
    exercise = st.session_state.get("exercise_type", "")
    if not session_id or not exercise:
        return

    if exercise == "Squats" and st.session_state.get("depth_status") == "TOO HIGH":
        log_form_event(session_id, exercise, "form_flaw", "squat_depth",
                       st.session_state.get("knee_angle"), "Squat depth insufficient — knees not bending enough.")
    elif exercise == "Push-ups" and st.session_state.get("hip_status") in ("SAGGING", "PIKED UP"):
        log_form_event(session_id, exercise, "form_flaw", "hip_position",
                       None, f"Hip {st.session_state.get('hip_status', '').lower()} detected.")
    elif exercise == "Biceps Curls (Dumbbell)":
        if st.session_state.get("swing_status") == "SWINGING":
            log_form_event(session_id, exercise, "form_flaw", "torso_swing",
                           None, "Torso swinging during curl.")
        if st.session_state.get("shoulder_status") == "ELBOW DRIFTING":
            log_form_event(session_id, exercise, "form_flaw", "elbow_drift",
                           None, "Elbow drifting away from body.")
    elif exercise == "Shoulder Press" and st.session_state.get("back_arch_status") == "Excessive Arch":
        log_form_event(session_id, exercise, "form_flaw", "back_arch",
                       None, "Excessive lower back arch.")
    elif exercise == "Lunges" and st.session_state.get("balance_status") == "OFF BALANCE":
        log_form_event(session_id, exercise, "form_flaw", "balance",
                       None, "Balance off — widen stance.")


def _generate_workout_summary(exercise: str, completed_sets: int, total_reps: int, duration: int) -> str:
    mins = duration // 60
    secs = duration % 60
    return (
        f"You completed {completed_sets} set(s) of {exercise} with {total_reps} total reps "
        f"in {mins}m {secs}s. Great effort! Focus on maintaining consistent form every rep."
    )


# ─────────────────────────────────────────────────────────────────────────────
# CARDIO / RUNNING & WALKING PAGE (GPS + Map + Real-Time Tracking)
# ─────────────────────────────────────────────────────────────────────────────
def _render_cardio_page():
    st.title("🏃 Running & Cardio Tracking")
    st.caption("Live GPS route mapping, real-time pace, speed & distance")

    if "cardio_tracker" not in st.session_state:
        st.session_state.cardio_tracker = CardioTracker(activity_type="Running")

    tracker: CardioTracker = st.session_state.cardio_tracker
    user_id = st.session_state.get("user_id", "")

    # Activity selection (when not active)
    if tracker.status == "idle":
        col_act, col_sim = st.columns([2, 1])
        with col_act:
            activity = st.selectbox("Activity Type", ["Running", "Walking"], key="cardio_act_select")
            tracker.activity_type = activity

    # GPS Bridge
    render_gps_collector(is_active=(tracker.status == "tracking"))

    # Map Rendering
    current_pos = None
    if tracker.last_valid_point:
        current_pos = (tracker.last_valid_point["latitude"], tracker.last_valid_point["longitude"])
    
    route_coords = [[p["latitude"], p["longitude"]] for p in tracker.route_points]
    render_map_component(route_coords=route_coords, current_pos=current_pos, height_px=380, is_active=(tracker.status == "tracking"))

    # Live Outdoor HUD
    elapsed = tracker.get_elapsed_seconds()
    moving = tracker.get_moving_seconds()
    dist_km = round(tracker.distance_meters / 1000.0, 2)

    st.markdown(
        f"""
        <div class="cardio-hud-box">
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:12px;">
                <span style="font-weight:700; color:#9ca3af; text-transform:uppercase; letter-spacing:0.05em;">
                    {tracker.activity_type} · Status: <span style="color:{'#10b981' if tracker.status == 'tracking' else '#f59e0b' if tracker.status == 'paused' else '#9ca3af'}">{tracker.status.upper()}</span>
                </span>
                <span style="font-size:12px; color:#6b7280;">GPS Quality Filter Active (Max ±50m)</span>
            </div>
            <div style="display:grid; grid-template-columns: repeat(auto-fit, minmax(130px, 1fr)); gap:16px;">
                <div>
                    <div style="font-size:12px; color:#9ca3af;">DISTANCE</div>
                    <div style="font-size:2rem; font-weight:800; color:#fff;">{dist_km} <span style="font-size:1rem; color:#9ca3af;">km</span></div>
                </div>
                <div>
                    <div style="font-size:12px; color:#9ca3af;">MOVING TIME</div>
                    <div style="font-size:2rem; font-weight:800; color:#fff;">{format_duration(moving)}</div>
                </div>
                <div>
                    <div style="font-size:12px; color:#9ca3af;">AVG PACE</div>
                    <div style="font-size:2rem; font-weight:800; color:#0ecfb5;">{tracker.average_pace_str}</div>
                </div>
                <div>
                    <div style="font-size:12px; color:#9ca3af;">AVG SPEED</div>
                    <div style="font-size:2rem; font-weight:800; color:#fff;">{tracker.average_speed_kmh} <span style="font-size:1rem; color:#9ca3af;">km/h</span></div>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )

    # Mobile-Friendly Thumb Action Buttons
    if tracker.status == "idle":
        if st.button("▶ START ACTIVITY", width="stretch", type="primary", key="btn_cardio_start"):
            tracker.start()
            st.session_state.cardio_session_id = create_cardio_session(str(user_id), tracker.activity_type)
            st.rerun()

    elif tracker.status == "tracking":
        col_p, col_f = st.columns(2)
        with col_p:
            if st.button("⏸ PAUSE", width="stretch", type="secondary", key="btn_cardio_pause"):
                tracker.pause()
                st.rerun()
        with col_f:
            if st.button("⏹ FINISH", width="stretch", type="primary", key="btn_cardio_finish"):
                tracker.finish()
                _persist_completed_cardio(tracker, str(user_id))
                st.session_state.cardio_just_finished = True
                st.rerun()

    elif tracker.status == "paused":
        col_r, col_f = st.columns(2)
        with col_r:
            if st.button("▶ RESUME", width="stretch", type="primary", key="btn_cardio_resume"):
                tracker.resume()
                st.rerun()
        with col_f:
            if st.button("⏹ FINISH", width="stretch", type="secondary", key="btn_cardio_finish_paused"):
                tracker.finish()
                _persist_completed_cardio(tracker, str(user_id))
                st.session_state.cardio_just_finished = True
                st.rerun()

    elif tracker.status == "completed":
        st.success("🎉 Activity complete! Route and performance metrics saved to your history.")
        if st.button("Start New Activity", width="stretch", type="primary", key="btn_cardio_reset"):
            st.session_state.cardio_tracker = CardioTracker(activity_type="Running")
            st.rerun()

    # Testing & GPS Movement Simulator (useful when running locally on desktop indoors)
    if tracker.status == "tracking":
        with st.expander("📍 GPS Step Simulator (For Indoor Testing)"):
            st.caption("If testing on a desktop computer indoors, click below to simulate runner movement coordinates.")
            if st.button("➕ Simulate 100m GPS Step Forward", width="stretch", key="btn_sim_step"):
                # Default baseline near Hyderabad or last position
                base_lat = tracker.last_valid_point["latitude"] if tracker.last_valid_point else 17.3850
                base_lng = tracker.last_valid_point["longitude"] if tracker.last_valid_point else 78.4867
                # Step ~0.0009 degrees north (~100 meters)
                new_lat = base_lat + 0.0009
                new_lng = base_lng + (0.0002 if len(tracker.route_points) % 2 == 0 else -0.0001)
                accepted = tracker.add_gps_sample(new_lat, new_lng, accuracy=8.0)
                if accepted:
                    session_id = st.session_state.get("cardio_session_id")
                    if session_id:
                        add_cardio_route_point(session_id, len(tracker.route_points), new_lat, new_lng, 8.0, 3.2)
                st.rerun()


def _persist_completed_cardio(tracker: CardioTracker, user_id: str):
    session_id = st.session_state.get("cardio_session_id")
    if not session_id:
        return
    complete_cardio_session(
        session_id=session_id,
        elapsed_sec=int(tracker.get_elapsed_seconds()),
        moving_sec=int(tracker.get_moving_seconds()),
        distance_meters=tracker.distance_meters,
        average_speed_kmh=tracker.average_speed_kmh,
        average_pace_sec=tracker.average_pace_sec
    )


# ─────────────────────────────────────────────────────────────────────────────
# RESULTS & TRANSFORMATION PAGE (Before & After Comparisons + Camera + Quotes)
# ─────────────────────────────────────────────────────────────────────────────
_MOTIVATIONAL_QUOTES = [
    ("Today's pain is tomorrow's gain.", "💪"),
    ("Discipline is everything — it builds attitude, behaviour, character and determination.", "🔥"),
    ("Your I CAN is always greater than your IQ.", "🧠"),
    ("The body achieves what the mind believes.", "🎯"),
    ("Push harder than yesterday if you want a different tomorrow.", "⚡"),
    ("Sweat now. Shine later.", "✨"),
    ("Champions are not born — they are built, rep by rep.", "🏆"),
]


def _img_to_bytes(img_data):
    """Convert stored image data (raw base64, data URI, or URL) to bytes for st.image()."""
    import base64 as _b64
    if not img_data:
        return None
    if isinstance(img_data, (bytes, bytearray)):
        return bytes(img_data)
    try:
        s = str(img_data).strip()
        if s.startswith("data:"):
            _, b64str = s.split(",", 1)
            return _b64.b64decode(b64str)
        elif s.startswith("http://") or s.startswith("https://"):
            return s  # plain URL — st.image() accepts strings for URLs
        else:
            # Assume raw base64
            return _b64.b64decode(s)
    except Exception:
        return None


def _render_results_page():
    import base64
    import time as _time
    from pathlib import Path

    st.title("📸 Results & Transformation")

    # ── Motivational Quote Banner ──────────────────────────────────────────────
    q_idx = int(_time.time() / 10) % len(_MOTIVATIONAL_QUOTES)
    quote_text, quote_emoji = _MOTIVATIONAL_QUOTES[q_idx]
    st.markdown(
        f"""
        <div style="background:linear-gradient(135deg,#0f172a 0%,#0a1a18 100%);
                    border:1px solid rgba(14,207,181,0.45); border-radius:14px;
                    padding:18px 24px; margin-bottom:20px; text-align:center;">
            <div style="font-size:1.8rem; margin-bottom:4px;">{quote_emoji}</div>
            <blockquote style="margin:0; font-size:1.05rem; font-weight:600;
                               color:#e5e7eb; font-style:italic; line-height:1.6;">
                &ldquo;{quote_text}&rdquo;
            </blockquote>
            <p style="color:#0ecfb5; font-size:11px; margin:6px 0 0 0; letter-spacing:.1em;">
                ADHI'S AI GYM COACH &nbsp;·&nbsp; DAILY MOTIVATION
            </p>
        </div>
        """,
        unsafe_allow_html=True
    )

    static_tf_dir = Path(__file__).resolve().parent / "static" / "transformations"
    img_b1 = str(static_tf_dir / "adhi_before_1.png")
    img_b2 = str(static_tf_dir / "adhi_before_2.png")
    img_a_side = str(static_tf_dir / "adhi_after_side.jpg")
    img_a_front = str(static_tf_dir / "adhi_after_front.jpg")
    img_a_back = str(static_tf_dir / "adhi_after_back.jpg")

    user_id = str(st.session_state.get("user_id", ""))
    records = get_transformation_records(user_id)

    # ═══════════════════════════════════════════════════════════════════════════
    # PRIMARY BEFORE & AFTER COMPARISON (Loaded with Adhi's Real Photos by Default)
    # ═══════════════════════════════════════════════════════════════════════════
    st.markdown(
        """
        <div style="display:flex; align-items:center; gap:10px; margin-bottom:14px;">
            <div style="height:2px; flex:1; background:linear-gradient(90deg,transparent,#0ecfb5);"></div>
            <span style="color:#0ecfb5; font-size:0.95rem; font-weight:800; letter-spacing:.1em;">
                BEFORE &amp; AFTER COMPARISON
            </span>
            <div style="height:2px; flex:1; background:linear-gradient(90deg,#0ecfb5,transparent);"></div>
        </div>
        """,
        unsafe_allow_html=True
    )

    disp_col_b, disp_col_a = st.columns(2)

    user_before = st.session_state.get("before_bytes")
    user_after = st.session_state.get("after_bytes")

    # ── BEFORE display panel ───────────────────────────────────────────────────
    with disp_col_b:
        st.markdown(
            """<div style="background:linear-gradient(180deg,#181d2b 0%,#0f1420 100%);
                           border:2px solid #374151; border-radius:12px; padding:12px 16px;
                           margin-bottom:12px; text-align:center;">
                <div style="font-size:1.15rem; font-weight:800; color:#e5e7eb; letter-spacing:.08em;">
                    📸 BEFORE PHOTO
                </div>
                <div style="color:#9ca3af; font-size:12px; margin-top:2px;">
                    Baseline Starting Point · Blue Plaid Dress / Casual
                </div>
            </div>""",
            unsafe_allow_html=True
        )

        b_tab_prof, b_tab_front, b_tab_custom = st.tabs([
            "🖼️ Profile View", 
            "🧍 Front Standing", 
            "📷 Personal Upload"
        ])

        with b_tab_prof:
            st.image(img_b1, caption="Before: Side Profile Leaning (Starting Baseline)", use_container_width=True)

        with b_tab_front:
            st.image(img_b2, caption="Before: Front Standing View (Casual Baseline)", use_container_width=True)

        with b_tab_custom:
            if user_before:
                st.image(user_before, caption="Your Uploaded BEFORE Photo", use_container_width=True)
                if st.button("🗑️ Remove Custom Before", key="rm_custom_b", use_container_width=True):
                    del st.session_state["before_bytes"]
                    st.rerun()
            else:
                st.markdown(
                    """<div style="background:#0f1420; border:2px dashed #4b5563; border-radius:10px;
                                   min-height:180px; display:flex; flex-direction:column;
                                   align-items:center; justify-content:center; text-align:center;
                                   padding:20px; color:#9ca3af; margin-bottom:12px;">
                        <div style="font-size:2.4rem; margin-bottom:6px;">📸</div>
                        <div style="font-size:0.95rem; font-weight:600; color:#e5e7eb;">Upload Your Personal BEFORE Photo</div>
                        <div style="font-size:0.8rem; color:#6b7280; margin-top:4px;">Use webcam capture or choose an image file below</div>
                    </div>""",
                    unsafe_allow_html=True
                )
            bc_cam, bc_up = st.tabs(["📷 Camera Capture", "📁 Upload File"])
            with bc_cam:
                b_cam = st.camera_input("Take BEFORE photo", key="cam_before", label_visibility="collapsed")
                if b_cam is not None:
                    st.session_state["before_bytes"] = b_cam.getvalue()
                    st.rerun()
            with bc_up:
                b_up = st.file_uploader("Choose BEFORE image", type=["jpg", "jpeg", "png", "webp"], key="up_before", label_visibility="collapsed")
                if b_up is not None:
                    st.session_state["before_bytes"] = b_up.read()
                    st.rerun()

    # ── AFTER display panel ────────────────────────────────────────────────────
    with disp_col_a:
        st.markdown(
            """<div style="background:linear-gradient(180deg,#0a1a18 0%,#041210 100%);
                           border:2px solid rgba(14,207,181,0.6); border-radius:12px; padding:12px 16px;
                           margin-bottom:12px; text-align:center; box-shadow:0 0 15px rgba(14,207,181,0.15);">
                <div style="font-size:1.15rem; font-weight:800; color:#0ecfb5; letter-spacing:.08em;">
                    ✨ AFTER TRANSFORMATION
                </div>
                <div style="color:#2dd4bf; font-size:12px; margin-top:2px;">
                    Peak Conditioning · Gym Showcase & Hypertrophy
                </div>
            </div>""",
            unsafe_allow_html=True
        )

        a_tab_side, a_tab_front, a_tab_back, a_tab_custom = st.tabs([
            "💪 Side Flex", 
            "⚡ Front Shredded", 
            "🦅 Back Lat Spread", 
            "📷 Personal Upload"
        ])

        with a_tab_side:
            st.image(img_a_side, caption="After: Side Flex — Biceps & Triceps Hypertrophy", use_container_width=True)

        with a_tab_front:
            st.image(img_a_front, caption="After: Front View — Shredded Abs & Shoulder Symmetry", use_container_width=True)

        with a_tab_back:
            st.image(img_a_back, caption="After: Back View — V-Taper Lat Spread & Trapezius", use_container_width=True)

        with a_tab_custom:
            if user_after:
                st.image(user_after, caption="Your Uploaded AFTER Photo", use_container_width=True)
                if st.button("🗑️ Remove Custom After", key="rm_custom_a", use_container_width=True):
                    del st.session_state["after_bytes"]
                    st.rerun()
            else:
                st.markdown(
                    """<div style="background:#050f0d; border:2px dashed rgba(14,207,181,0.4);
                                   border-radius:10px; min-height:180px; display:flex;
                                   flex-direction:column; align-items:center; justify-content:center;
                                   text-align:center; padding:20px; color:#0ecfb5; margin-bottom:12px;">
                        <div style="font-size:2.4rem; margin-bottom:6px;">💪</div>
                        <div style="font-size:0.95rem; font-weight:600; color:#0ecfb5;">Upload Your Personal AFTER Photo</div>
                        <div style="font-size:0.8rem; color:#1d6b60; margin-top:4px;">Use webcam capture or choose an image file below</div>
                    </div>""",
                    unsafe_allow_html=True
                )
            ac_cam, ac_up = st.tabs(["📷 Camera Capture", "📁 Upload File"])
            with ac_cam:
                a_cam = st.camera_input("Take AFTER photo", key="cam_after", label_visibility="collapsed")
                if a_cam is not None:
                    st.session_state["after_bytes"] = a_cam.getvalue()
                    st.rerun()
            with ac_up:
                a_up = st.file_uploader("Choose AFTER image", type=["jpg", "jpeg", "png", "webp"], key="up_after", label_visibility="collapsed")
                if a_up is not None:
                    st.session_state["after_bytes"] = a_up.read()
                    st.rerun()

    st.divider()

    # ── High Level Stats Bar ───────────────────────────────────────────────────
    st.markdown("### 📊 Transformation Metrics & Body Composition")
    s1, s2, s3, s4 = st.columns(4)
    with s1:
        st.metric("⚖️ Weight", "74.0 kg", delta="-10.0 kg Shred")
    with s2:
        st.metric("🔥 Body Fat", "11.2%", delta="-11.3% Fat Loss")
    with s3:
        st.metric("📏 Waist", "78.0 cm", delta="-14.0 cm Drop")
    with s4:
        st.metric("🎯 Form Precision", "96.8%", delta="+42% AI Guard")

    st.divider()

    # ── Complete 5-Photo Gallery ───────────────────────────────────────────────
    st.markdown("### 🖼️ Complete Transformation Photo Archive")
    st.caption("All 5 high-resolution photos: Casual baseline (Before) vs Full-body gym conditioning (After).")

    g_c1, g_c2, g_c3, g_c4, g_c5 = st.columns(5)
    with g_c1:
        st.markdown("<b style='color:#9ca3af; font-size:12px;'>📸 BEFORE 1</b>", unsafe_allow_html=True)
        st.image(img_b1, use_container_width=True)
        st.caption("Lakeside Profile")
    with g_c2:
        st.markdown("<b style='color:#9ca3af; font-size:12px;'>📸 BEFORE 2</b>", unsafe_allow_html=True)
        st.image(img_b2, use_container_width=True)
        st.caption("Front Casual")
    with g_c3:
        st.markdown("<b style='color:#0ecfb5; font-size:12px;'>✨ AFTER 1</b>", unsafe_allow_html=True)
        st.image(img_a_side, use_container_width=True)
        st.caption("Side Biceps Flex")
    with g_c4:
        st.markdown("<b style='color:#0ecfb5; font-size:12px;'>✨ AFTER 2</b>", unsafe_allow_html=True)
        st.image(img_a_front, use_container_width=True)
        st.caption("Front Core & Shoulders")
    with g_c5:
        st.markdown("<b style='color:#0ecfb5; font-size:12px;'>✨ AFTER 3</b>", unsafe_allow_html=True)
        st.image(img_a_back, use_container_width=True)
        st.caption("Back Lat Spread")

    st.divider()

    # ── Log Personal Milestone Form ────────────────────────────────────────────
    with st.expander("➕ Log a Personal Transformation Milestone (With Your Photos)", expanded=(len(records) == 0)):
        st.caption("📷 Capture or upload your own photos in the comparison box above, then save your milestone.")
        with st.form("transform_form"):
            c_w, c_bf = st.columns(2)
            with c_w:
                weight = st.number_input("Weight (kg)", min_value=30.0, max_value=250.0, value=74.0, step=0.1)
            with c_bf:
                bf = st.number_input("Body Fat %", min_value=3.0, max_value=60.0, value=11.5, step=0.5)
            c_c, c_wa, c_ar = st.columns(3)
            with c_c:
                chest = st.number_input("Chest (cm)", min_value=0.0, max_value=200.0, value=102.0, step=0.5)
            with c_wa:
                waist = st.number_input("Waist (cm)", min_value=0.0, max_value=200.0, value=78.0, step=0.5)
            with c_ar:
                arms = st.number_input("Arms (cm)", min_value=0.0, max_value=100.0, value=38.5, step=0.5)
            notes = st.text_input("Milestone Notes", placeholder="e.g. Completed 12-week AI Form training cycle!")
            submitted = st.form_submit_button("💾 Save Milestone to History", use_container_width=True)

        if submitted:
            def _to_b64(raw): return base64.b64encode(raw).decode("utf-8") if raw else None
            ok = save_transformation_record(
                user_id=user_id,
                weight_kg=weight,
                body_fat_pct=bf,
                chest_cm=chest if chest > 0 else None,
                waist_cm=waist if waist > 0 else None,
                arms_cm=arms if arms > 0 else None,
                notes=notes,
                before_img_data=_to_b64(st.session_state.get("before_bytes")),
                after_img_data=_to_b64(st.session_state.get("after_bytes"))
            )
            if ok:
                st.session_state.pop("before_bytes", None)
                st.session_state.pop("after_bytes", None)
                st.success("✅ Milestone saved with your Before & After photos!")
                st.rerun()
            else:
                st.error("Could not save. Please try again.")

    # ── Saved Personal Records ─────────────────────────────────────────────────
    if records:
        st.divider()
        st.subheader("📁 Saved Personal Milestone History")
        for rec in reversed(records):
            date_label = rec.get("recorded_date", "Recent")
            note_text = rec.get("notes", "")
            st.markdown(
                f"""<div style="background:#111520; border-left:3px solid #0ecfb5;
                                padding:8px 16px; border-radius:6px; margin-bottom:12px;">
                    <b style="color:#fff;">📅 {date_label}</b>
                    {"  &nbsp;·&nbsp; <span style='color:#9ca3af;font-size:12px;'>" + note_text + "</span>" if note_text else ""}
                </div>""",
                unsafe_allow_html=True
            )

            b_img = _img_to_bytes(rec.get("before_img_data"))
            a_img = _img_to_bytes(rec.get("after_img_data"))

            col_b, col_a = st.columns(2)
            with col_b:
                st.markdown("<div style='text-align:center; color:#9ca3af; font-size:11px; font-weight:700;'>📸 BEFORE</div>", unsafe_allow_html=True)
                if b_img:
                    st.image(b_img, use_container_width=True)
                else:
                    st.markdown("<div style='background:#181d2b; border:2px dashed #374151; border-radius:8px; padding:32px; text-align:center; color:#4b5563;'>📸 No Photo</div>", unsafe_allow_html=True)
            with col_a:
                st.markdown("<div style='text-align:center; color:#0ecfb5; font-size:11px; font-weight:700;'>✨ AFTER</div>", unsafe_allow_html=True)
                if a_img:
                    st.image(a_img, use_container_width=True)
                else:
                    st.markdown("<div style='background:#050f0d; border:2px dashed rgba(14,207,181,0.3); border-radius:8px; padding:32px; text-align:center; color:#0ecfb5;'>✨ No Photo</div>", unsafe_allow_html=True)

            sc1, sc2, sc3, sc4 = st.columns(4)
            sc1.metric("⚖️", f"{rec.get('weight_kg','—')} kg", label_visibility="collapsed")
            sc2.metric("🔥", f"{rec.get('body_fat_pct','—')}%", label_visibility="collapsed")
            sc3.metric("📐", f"{rec.get('chest_cm','—')} cm", label_visibility="collapsed")
            sc4.metric("📏", f"{rec.get('waist_cm','—')} cm", label_visibility="collapsed")
            st.divider()


def _render_history():
    st.title("📋 Workout & Cardio History")
    user_id = st.session_state.get("user_id", "")
    strength_history = get_users_exercises(str(user_id))
    cardio_history = get_user_cardio_sessions(str(user_id))

    tab_all, tab_strength, tab_cardio = st.tabs(["🌐 ALL ACTIVITIES", "🏋️ STRENGTH", "🏃 RUNNING & CARDIO"])

    with tab_all:
        rows = []
        for r in strength_history:
            rows.append({
                "Date": str(r.get("created_at", ""))[:10],
                "Category": "Strength",
                "Activity": r.get("exercise_name", ""),
                "Reps / Distance": f"{r.get('reps', 0)} reps",
                "Duration": f"{r.get('time', 0)}s"
            })
        for c in cardio_history:
            dist = round(c.get("distance_meters", 0.0) / 1000.0, 2)
            rows.append({
                "Date": str(c.get("started_at", ""))[:10],
                "Category": "Cardio",
                "Activity": c.get("activity_type", "Running"),
                "Reps / Distance": f"{dist} km",
                "Duration": format_duration(c.get("moving_seconds", 0))
            })

        if rows:
            df = pd.DataFrame(rows)
            df.sort_values(by="Date", ascending=False, inplace=True)
            df.reset_index(drop=True, inplace=True)
            df.index += 1
            st.dataframe(df, use_container_width=True)

            csv = df.to_csv(index=False).encode("utf-8")
            st.download_button("📥 Download Combined History CSV", data=csv, file_name="adhi_gym_combined_history.csv", mime="text/csv")
        else:
            st.info("No recorded activity yet. Complete a workout or cardio run to see records here!")

    with tab_strength:
        if strength_history:
            df_str = pd.DataFrame([{
                "Date": str(r.get("created_at", ""))[:10],
                "Exercise": r.get("exercise_name", ""),
                "Reps": int(r.get("reps", 0)),
                "Sets": int(r.get("sets", 1)),
                "Time (sec)": int(r.get("time", 0)),
            } for r in strength_history])
            st.dataframe(df_str, use_container_width=True)
        else:
            st.info("No strength sessions found.")

    with tab_cardio:
        if cardio_history:
            for session in cardio_history:
                session_id = session.get("id")
                dist_km = round(session.get("distance_meters", 0.0) / 1000.0, 2)
                moving_sec = session.get("moving_seconds", 0)
                started = str(session.get("started_at", ""))[:19]

                with st.expander(f"🏃 {session.get('activity_type','Run')} · {dist_km} km on {started[:10]}"):
                    c1, c2, c3, c4 = st.columns(4)
                    with c1:
                        st.metric("Distance", f"{dist_km} km")
                    with c2:
                        st.metric("Duration", format_duration(moving_sec))
                    with c3:
                        st.metric("Avg Speed", f"{session.get('average_speed_kmh', 0.0)} km/h")
                    with c4:
                        pace_s = session.get("average_pace_sec_per_km", 0.0)
                        mins, secs = divmod(int(pace_s), 60)
                        st.metric("Avg Pace", f"{mins:02d}:{secs:02d} /km" if pace_s > 0 else "--:-- /km")

                    # Route Map Replay
                    points = get_cardio_route_points(session_id)
                    if points:
                        coords = [[p["latitude"], p["longitude"]] for p in points]
                        render_map_component(route_coords=coords, height_px=280)
                    else:
                        st.caption("No GPS route points saved for this session.")

                    if st.button("🗑️ Delete Session & Route", key=f"del_cardio_{session_id}"):
                        delete_cardio_session(session_id)
                        st.success("Cardio session deleted.")
                        st.rerun()
        else:
            st.info("No cardio runs or walks logged yet.")


# ─────────────────────────────────────────────────────────────────────────────
# ANALYTICS PAGE (Strength + Cardio)
# ─────────────────────────────────────────────────────────────────────────────
def _render_analytics():
    st.title("📊 Progress Analytics")
    user_id = st.session_state.get("user_id", "")
    stats = get_user_stats(str(user_id))
    exercises = get_users_exercises(str(user_id))
    cardios = get_user_cardio_sessions(str(user_id))

    mins, secs = divmod(stats["total_time_sec"], 60)
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.metric("🏋️ Workouts", stats["total_workouts"])
    with c2:
        st.metric("🔁 Total Reps", f"{stats['total_reps']:,}")
    with c3:
        st.metric("🏃 Total Run", f"{stats.get('total_cardio_distance_km', 0.0)} km")
    with c4:
        st.metric("⏱️ Training Time", f"{mins}m {secs}s")

    st.divider()

    tab1, tab2, tab3 = st.tabs(["📈 Strength Volume", "🏃 Cardio Mileage", "🥧 Mix"])

    with tab1:
        if exercises:
            df = pd.DataFrame([{
                "Exercise": r.get("exercise_name", ""),
                "Reps": int(r.get("reps", 0))
            } for r in exercises])
            vol = df.groupby("Exercise")["Reps"].sum().sort_values(ascending=False)
            st.bar_chart(vol, color="#0ecfb5")
        else:
            st.info("Log strength workouts to view volume charts.")

    with tab2:
        if cardios:
            c_df = pd.DataFrame([{
                "Date": str(c.get("started_at", ""))[:10],
                "Distance (km)": round(c.get("distance_meters", 0.0) / 1000.0, 2)
            } for c in cardios])
            c_chart = c_df.groupby("Date")["Distance (km)"].sum()
            st.bar_chart(c_chart, color="#3b82f6")
        else:
            st.info("Log cardio runs or walks to view mileage trends.")

    with tab3:
        mix_data = {
            "Strength Sessions": stats.get("total_strength_workouts", 0),
            "Cardio Sessions": stats.get("total_cardio_sessions", 0)
        }
        st.dataframe(pd.DataFrame(list(mix_data.items()), columns=["Type", "Count"]), use_container_width=True)


# ─────────────────────────────────────────────────────────────────────────────
# CHATBOT — Ask Adhi Coach (Context-Aware Strength + Cardio)
# ─────────────────────────────────────────────────────────────────────────────
def _render_chatbot():
    st.title("🤖 Ask Adhi Coach")
    st.markdown(
        "I'm your personal AI coach powered by your actual workout and running data. "
        "Ask me anything about your training, diet, meal plans, running pace, or progress!"
    )

    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []

    user_id = st.session_state.get("user_id", "")
    exercises = get_users_exercises(str(user_id))
    cardios = get_user_cardio_sessions(str(user_id))
    stats = get_user_stats(str(user_id))

    # Display conversation
    for msg in st.session_state.chat_history:
        with st.chat_message(msg["role"]):
            st.write(msg["content"])

    # Starter questions
    if not st.session_state.chat_history:
        st.markdown("##### 💡 Try asking:")
        prompts = [
            "What should I eat for lean muscle gain?",
            "How far did I run this week?",
            "What was my average running pace?",
            "What should I focus on next workout?",
        ]
        cols = st.columns(2)
        for i, prompt in enumerate(prompts):
            if cols[i % 2].button(prompt, key=f"starter_{i}"):
                st.session_state.chat_history.append({"role": "user", "content": prompt})
                st.rerun()

    question = st.chat_input("Ask your coach anything about your workout, diet, or running...")

    if question:
        st.session_state.chat_history.append({"role": "user", "content": question})
        answer = _get_coach_answer(question, exercises, cardios, stats)
        st.session_state.chat_history.append({"role": "assistant", "content": answer})
        st.rerun()


def _get_coach_answer(question: str, exercises: list, cardios: list, stats: dict) -> str:
    """Build context-aware coaching response using user's strength + cardio records and multi-model LLM."""
    context = (
        f"The user has completed {stats['total_reps']} total strength reps and {stats.get('total_cardio_distance_km', 0.0)} km of cardio. "
        f"Their favorite exercise is {stats['favorite_exercise']}. "
    )
    if cardios:
        latest_c = cardios[0]
        dist_km = round(latest_c.get("distance_meters", 0.0) / 1000.0, 2)
        context += f"Latest cardio: {latest_c.get('activity_type', 'Run')} of {dist_km} km at {latest_c.get('average_speed_kmh', 0.0)} km/h. "

    # Medical disclaimer check
    medical_terms = ["injury", "pain", "hurt", "doctor", "medical", "diagnose", "disease"]
    if any(term in question.lower() for term in medical_terms):
        return (
            "I'm an AI workout coach, not a medical professional. If you're experiencing severe pain or injury, "
            "please consult a qualified healthcare provider. I can help with exercise technique, "
            "meal plans, rep tracking, running pace, and fitness guidance."
        )

    # 1. Try Google Gemini if configured
    gemini_key = os.environ.get("GEMINI_API_KEY", "")
    try:
        if not gemini_key and hasattr(st, "secrets") and "GEMINI_API_KEY" in st.secrets:
            gemini_key = st.secrets["GEMINI_API_KEY"]
    except Exception:
        pass

    if gemini_key and gemini_key.startswith("AIzaSy"):
        try:
            import requests
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={gemini_key}"
            prompt = (
                f"You are Adhi's AI Gym Coach — a knowledgeable, encouraging personal trainer and sports nutritionist. "
                f"User workout context: {context}. "
                f"User question: {question}. "
                f"Provide concise, motivating, actionable advice (3-5 sentences). NEVER diagnose medical conditions."
            )
            res = requests.post(url, json={"contents": [{"parts": [{"text": prompt}]}]}, timeout=6.0)
            if res.status_code == 200:
                data = res.json()
                text = data["candidates"][0]["content"]["parts"][0]["text"].strip()
                if text:
                    return text
        except Exception:
            pass

    # 2. Try Groq with candidate models
    groq_key = os.environ.get("GROQ_API_KEY", "")
    try:
        if not groq_key and hasattr(st, "secrets") and "GROQ_API_KEY" in st.secrets:
            groq_key = st.secrets["GROQ_API_KEY"]
    except Exception:
        pass

    if groq_key:
        try:
            client = Groq(api_key=groq_key)
            messages = [
                {"role": "system", "content": (
                    "You are Adhi's AI Gym Coach — a knowledgeable, encouraging personal trainer and fitness nutritionist. "
                    "You give direct, actionable advice on workouts, diet, meal plans, rep cadence, and endurance. "
                    "Keep responses concise (3-5 sentences or structured bullet points). "
                    f"User workout context: {context}"
                )},
                {"role": "user", "content": question}
            ]
            candidate_models = ["openai/gpt-oss-120b", "qwen/qwen3.8-27b", "openai/gpt-oss-20b", "groq/compound-mini"]
            for m in candidate_models:
                try:
                    response = client.chat.completions.create(
                        model=m,
                        messages=messages,
                        temperature=0.5,
                        timeout=6.0,
                    )
                    text = response.choices[0].message.content.strip()
                    if text:
                        return text
                except Exception:
                    continue
        except Exception:
            pass

    # Deterministic fallback answers
    q = question.lower()
    if "meal" in q or "food" in q or "eat" in q or "diet" in q:
        return (
            "🥗 **High-Protein Nutrition Plan for Muscle Growth & Fat Loss:**\n"
            "- **Breakfast:** 3 whole eggs + 2 whites, rolled oats with berries and a spoonful of peanut butter.\n"
            "- **Lunch:** Grilled chicken breast (or paneer/tofu), brown rice/quinoa, and green veggies.\n"
            "- **Post-Workout:** Whey protein shake with a banana for rapid glycogen replenishment.\n"
            "- **Dinner:** Grilled fish/lean meat, sweet potato, and avocado salad.\n"
            "- **Hydration:** Aim for 3-4 liters of water daily!"
        )
    if "how far" in q or "run" in q or "distance" in q:
        tot_km = stats.get("total_cardio_distance_km", 0.0)
        return f"You've tracked a total of {tot_km} km across your logged cardio sessions. Keep clocking those miles!"
    if "pace" in q:
        if cardios:
            p_sec = cardios[0].get("average_pace_sec_per_km", 0.0)
            mins, secs = divmod(int(p_sec), 60)
            return f"Your latest run had an average pace of {mins:02d}:{secs:02d} /km. Great consistency!"
        return "You haven't logged any cardio sessions yet. Take the app on a run or walk to measure your pace!"
    if "last workout" in q:
        if exercises:
            r = exercises[0]
            return f"Your most recent strength session was {r.get('exercise_name', 'an exercise')} with {r.get('reps', 0)} reps."
        return "I don't see any workout history yet. Start your first strength or cardio session to build your log!"
    return (
        f"Great question! Based on your activity ({stats['total_reps']} strength reps and {stats.get('total_cardio_distance_km', 0.0)} km cardio), "
        "you're building balanced athleticism. Focus on progressive overload in strength and smooth aerobic base building in your runs."
    )


# ─────────────────────────────────────────────────────────────────────────────
# PROFILE PAGE
# ─────────────────────────────────────────────────────────────────────────────
def _render_profile():
    from services.persistence.exercise_repository import get_user_profile, update_user_profile

    st.title("👤 Profile")
    user_id = str(st.session_state.get("user_id", ""))
    username = st.session_state.get("username", "")

    profile = get_user_profile(user_id) or {}

    with st.form("profile_form"):
        st.markdown("#### Update Your Profile")
        display_name = st.text_input("Display Name", value=profile.get("display_name", username))
        age = st.number_input("Age (optional)", min_value=0, max_value=120, step=1,
                              value=int(profile.get("age") or 0))
        height = st.number_input("Height in cm (optional)", min_value=0.0, max_value=300.0, step=0.5,
                                 value=float(profile.get("height_cm") or 0.0))
        experience = st.selectbox("Experience Level",
                                  ["Beginner", "Intermediate", "Advanced"],
                                  index=["Beginner", "Intermediate", "Advanced"].index(
                                      profile.get("experience_level", "Beginner")))
        submitted = st.form_submit_button("Save Profile", width='stretch')

    if submitted:
        ok = update_user_profile(
            user_id,
            display_name=display_name,
            age=age if age > 0 else None,
            height_cm=height if height > 0 else None,
            experience_level=experience
        )
        if ok:
            st.session_state.username = display_name
            st.success("✅ Profile updated successfully!")
        else:
            st.error("Could not save profile changes.")

    st.divider()
    st.markdown("#### Account & Privacy Info")
    st.caption(f"**Email:** {st.session_state.get('user_email', 'N/A')}")
    st.caption(f"**Cloud Sync:** {'✅ Active' if st.session_state.get('is_cloud_user') else '⚠️ Offline (local only)'}")
    st.markdown(
        """
        🔒 **Location & Camera Privacy:**<br>
        - Camera frames are processed strictly in-memory by MediaPipe and are never recorded or saved.<br>
        - GPS location coordinates are captured exclusively when you tap START in Running / Cardio mode, and tracking immediately ceases when you tap FINISH.<br>
        - All saved route data is isolated by user account using Supabase Row Level Security (RLS).
        """,
        unsafe_allow_html=True
    )


if __name__ == "__main__":
    main()
