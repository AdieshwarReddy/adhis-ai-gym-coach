# ADHI'S AI GYM COACH — 15-PHASE MASTER IMPLEMENTATION PLAN

**Project Name:** ADHI'S AI GYM COACH  
**Subtitle:** Real-Time AI Fitness Form Analysis, Rep Tracking & Intelligent Coaching Platform  
**Target:** Final-Year B.Tech AI/ML Capstone & Top-Tier Engineering Portfolio  
**Philosophy:** Technical truth, zero fake metrics, resilient fallbacks, free-tier deployment, absolute preservation of working computer vision core.

---

## 1. Architectural Blueprint

```
[ WEBCAM FEED (H.264/VP8 via streamlit-webrtc) ]
                    │
                    ▼
[ VIDEO PROCESSOR (`services/vision/exercise_video_processor.py`) ]
                    │  - BGR -> RGB frame conversion
                    │  - MediaPipe Tasks PoseLandmarker (33 3D landmarks)
                    │  - Landmark visibility filtering (> 0.70)
                    │
                    ▼
[ BIOMECHANICAL GEOMETRY ENGINE (`core/base_exercise.py`) ]
                    │  - Vector dot product & norm angle: θ = arccos(u·v / |u||v|)
                    │  - Safe math clamping [-1.0, 1.0]
                    │
                    ▼
[ EXERCISE FINITE-STATE MACHINES (`detectors/`) ]
  ├─ Biceps Curl (Elbow angle, elbow drift, torso swing)
  ├─ Squat (Knee angle, depth categorization, back lean)
  ├─ Push-up (Elbow angle, body collinearity, hip sag/pike)
  ├─ Shoulder Press (Elbow extension, lumbar arch)
  └─ Lunges (Bilateral knee tracking, dynamic leg selection, balance)
                    │
                    ▼
[ HUD OVERLAY & REAL-TIME EVENT ENGINE ]
  ├─ Real-time OpenCV landmarks, angles, stages, and cues
  ├─ Debounced form event logging (cooldown timer)
  ├─ Rep counter & target sets state machine
                    │
                    ▼
[ DUAL PERSISTENCE & MULTI-USER CLOUD ARCHITECTURE ]
  ├─ Local Fallback: SQLite (`Main App/data.db`)
  └─ Production Cloud: Supabase PostgreSQL + Supabase Auth + RLS Policies
       ├─ profiles (id, auth_user_id, display_name, created_at)
       ├─ workout_sessions (id, user_id, started_at, completed_at, duration_seconds, status)
       ├─ exercise_sets (id, session_id, exercise_type, set_number, target_reps, completed_reps)
       ├─ form_events (id, session_id, exercise_type, event_type, metric_name, metric_value, message)
       └─ workout_summaries (id, session_id, total_reps, completed_sets, duration_seconds, coach_summary)
                    │
                    ▼
[ INTELLIGENT COACHING & VOICE SUBSYSTEM ]
  ├─ Deterministic Rule Coach (0ms local safety cues)
  ├─ Groq LLaMA 3.3-70B API (Contextual coach & Ask Adhi Chatbot)
  └─ Voice Feedback: Browser SpeechSynthesis + Audio Byte Caching
```

---

## 2. 15 Structured Implementation Phases

### PHASE 1: Audit Current Working Localhost App
- Inspect complete repository, dependencies, video pipeline, and login behavior.
- Document findings across all 14 mandatory areas in `docs/PROJECT_AUDIT.md`.
- Verify localhost Streamlit app is up and running on port 8501.

### PHASE 2: Verify All 5 Exercises
- Run and verify all 5 core detectors: Biceps Curl, Squat, Push-up, Shoulder Press, Lunges.
- Verify angle calculations, rep counting, stage transitions, and debounce mechanisms via unit tests and synthetic landmark feeds.
- Ensure zero detector crashes or regressions.

### PHASE 3: Refactor Configuration & Secrets
- Create `.env.example` with clean template variables (`SUPABASE_URL`, `SUPABASE_ANON_KEY`, `GROQ_API_KEY`, etc.).
- Ensure `.env` is ignored in `.gitignore`.
- Support both environment variables and Streamlit secrets (`st.secrets`) with safe `try...except` handling.
- Verify zero hardcoded secrets exist across codebase.

### PHASE 4: Supabase Setup & Relational Schema
- Author comprehensive guide `docs/SUPABASE_SETUP.md` (free-tier setup, project creation, API keys, RLS).
- Create production SQL migration file `migrations/01_initial_schema.sql`:
  - `profiles`
  - `workout_sessions`
  - `exercise_sets`
  - `form_events`
  - `workout_summaries`
- Configure Row Level Security (RLS) policies guaranteeing multi-user tenant isolation.
- Create `docs/DATABASE.md`.

### PHASE 5: Production Authentication
- Create Supabase Auth client wrapper in `services/auth/supabase_auth.py`.
- Build professional UI for Sign Up, Sign In, Sign Out, and Profile management.
- Provide user-friendly error handling (duplicate email, invalid credentials, short passwords).
- Maintain seamless session persistence and fallback for offline local mode.
- Create `docs/AUTHENTICATION.md`.

### PHASE 6: Cloud Workout Persistence & Event-Based Form Logging
- Upgrade `exercise_repository.py` to support the normalized relational schema.
- Implement event-based form logging with a 2-second cooldown to eliminate frame-rate spamming.
- Session lifecycle: create session on start -> record sets on completion -> record deduplicated form events -> summarize on end.

### PHASE 7: Dashboard & Workout History
- Build authenticated dashboard: Welcome banner, KPI cards (Total Workouts, Total Reps, Weekly Sessions, Current Streak, Favorite Exercise), and Quick Start CTA.
- Build detailed Workout History view: Session cards, expandable set-by-set breakdown, form violation analysis, and CSV export.

### PHASE 8: Progress Analytics
- Interactive charts and KPI metrics powered by verified database records.
- Metrics: Weekly volume, reps by exercise, exercise distribution, workout duration trends, and common form flaws.
- Strict anti-fabrication policy: Charts display only true user activity.

### PHASE 9: Ask Adhi Coach Chatbot
- Build dedicated "Ask Adhi Coach" page.
- Context-aware RAG pipeline: retrieves user's recent workout sessions and common form errors from Supabase, formats a structured prompt, and queries Groq LLaMA 3.3.
- Medical disclaimers and safety guardrails.
- Robust deterministic fallback if Groq API is offline or unconfigured.

### PHASE 10: Workout AI Summary & Voice Coach
- Post-workout summary generator summarizing sets, reps, volume, and top form corrections.
- Voice Coach: On/Off toggle in sidebar, debounce interval (minimum 5s between speech cues), cached speech audio buffers, and browser SpeechSynthesis support.
- Document in `docs/LLM_COACH.md` and `docs/VOICE_COACH.md`.

### PHASE 11: UI/UX Polish & Modern Multi-Page Experience
- Implement unified cyber-gym dark theme (graphite background, cyan/amber neon accents).
- Sidebar navigation: Dashboard, Start Workout, Live Workout, History, Progress, Ask Adhi Coach, Profile, Logout.
- Responsive HUD layout with clear status badges (No Pose, In Frame, Active Set, Rest Interval).

### PHASE 12: Automated Testing Suite
- Expand pytest suite to cover all edge cases:
  - Base geometry & angle clamping
  - All 5 detector state machines and debounce logic
  - Low-visibility suppression
  - Set progression and session completion
  - Supabase/SQLite repository operations
  - LLM fallback and voice caching
- Document in `docs/TESTING.md`.

### PHASE 13: Performance Benchmarking
- Build standalone benchmark script `scripts/benchmark_vision.py`.
- Measure MediaPipe inference time, detector calculation time, OpenCV annotation latency, and overall FPS across resolutions.
- Publish verified, empirical numbers in `docs/PERFORMANCE.md`.

### PHASE 14: Cloud Deployment
- Configure Streamlit Community Cloud readiness (`packages.txt`, `requirements.txt`, `.streamlit/config.toml`, STUN ICE server configs).
- Configure GitHub Pages for static `LandingPage`.
- Test camera access over HTTPS.
- Create `docs/DEPLOYMENT.md`.

### PHASE 15: Comprehensive Documentation & Academic Portfolio
- Create complete documentation suite:
  - `README.md` (Executive overview, architecture, quickstart, setup, benchmarks, acknowledgments)
  - `docs/ARCHITECTURE.md`, `docs/POSE_PIPELINE.md`, `docs/EXERCISE_DETECTORS.md`, `docs/REP_COUNTING.md`, `docs/FORM_FEEDBACK.md`, `docs/PRIVACY.md`, `docs/LIMITATIONS.md`.
- Ensure strict academic attribution in `ACKNOWLEDGMENTS.md`.
- Placement/Interview preparation notes (system design, computer vision fundamentals, viva questions).
