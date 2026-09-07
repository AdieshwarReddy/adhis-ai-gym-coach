# ADHI'S AI GYM COACH — COMPREHENSIVE PROJECT AUDIT

**Date:** September 7, 2026  
**Project:** Adhi's AI Gym Coach  
**Subtitle:** Real-Time AI Fitness Form Analysis, Rep Tracking & Intelligent Coaching Platform  
**Lead Engineer:** Adhi (Final-Year B.Tech AI/ML)  
**Status:** Working Localhost Prototype Audited & Verified  

---

## 1. WHAT CURRENTLY WORKS

- **MediaPipe Pose Tracking:** `ml_models/pose_landmarker_full.task` initializes cleanly via TensorFlow Lite XNNPACK CPU delegate. Accurately tracks 33 3D normalized body landmarks with visibility confidence scores.
- **WebRTC Camera Pipeline:** `streamlit-webrtc` delivers live webcam frames into `VideoProcessorClass` asynchronously without blocking the UI thread.
- **Biomechanical Angle Calculations:** `core/base_exercise.py` implements vector dot product angle calculation:
  $$\theta = \arccos\left(\frac{\mathbf{u} \cdot \mathbf{v}}{\|\mathbf{u}\| \|\mathbf{v}\|}\right)$$
  Clamped to $[-1.0, 1.0]$ to prevent domain errors.
- **All 5 Core Exercise Detectors:**
  1. **Biceps Curls:** Bilateral visibility selection, elbow angle ($<50^\circ$ UP, $>160^\circ$ DOWN), elbow drift ($\Delta x \le 0.06$), torso swing detection ($\theta \le 15^\circ$).
  2. **Squats:** Knee angle, depth status (DEEP, PARALLEL, TOO HIGH), torso lean angle.
  3. **Push-ups:** Elbow angle ($<90^\circ$ DOWN, $>160^\circ$ UP), shoulder-hip-ankle collinearity ($>160^\circ$), hip sag/pike tracking ($\Delta y \le 0.08$).
  4. **Shoulder Press:** Bilateral arm extension ($>160^\circ$), lower back arch monitoring.
  5. **Lunges:** Dynamic front leg selection, bilateral knee angles ($<100^\circ$ DOWN), lateral torso balance offset ($|x_{sh} - x_{hip}| \le 0.10$).
- **Live Visual HUD:** Real-time OpenCV skeletal landmark overlay, colored joint angles, stage badge, and form alerts directly on the video stream.
- **Sets & Rep Tracking:** Target sets and reps progression with automatic set completion detection.
- **Persistence:** Local SQLite fallback database (`data.db`) storing user exercises, reps, sets, and active duration.
- **Performance Analytics:** Streamlit dashboard showing summary cards (Total Reps, Total Sets, Active Time), volume bar chart, and CSV export.
- **Coaching Engine Fallback:** `services/coaching/llm.py` provides instant deterministic rule-based feedback if Groq API key is absent or network fails.
- **Automated Tests:** 22/22 pytest unit tests passing in `.venv` (Python 3.12.1).

---

## 2. WHAT DOES NOT WORK

- **Production Cloud Authentication:** Currently uses an insecure single-field username form (`services/auth/login_wall.py`) without passwords, email verification, or session tokens.
- **Supabase Cloud Schema:** Database tables are flat (`users`, `exercises`) rather than the normalized schema (`profiles`, `workout_sessions`, `exercise_sets`, `form_events`, `workout_summaries`) with Row Level Security (RLS).
- **Interactive Workout Chatbot:** "Ask Adhi Coach" chatbot page is not yet implemented.
- **Event-Based Form Logging:** Form errors are rendered transiently in HUD rather than logged to a dedicated `form_events` table with debounce/cooldown.
- **High-Performance Voice Engine:** Relies exclusively on `gTTS` network requests (300-800ms lag) without phrase caching or browser SpeechSynthesis API.
- **Automated Vision Benchmark:** `scripts/benchmark_vision.py` and empirical `docs/PERFORMANCE.md` are not yet created.

---

## 3. CURRENT LOGIN STATUS

- **Implementation:** `services/auth/login_wall.py` renders a simple text input asking for a unique name.
- **Storage:** Creates a record in SQLite `users` table (`id`, `name`, `created_at`).
- **Security:** Zero password hashing, zero session validation, zero token persistence. Anyone entering the same username gains access to that user's workout history.
- **Required Upgrade:** Full Supabase Auth (Sign Up, Sign In, Sign Out, Password Reset) with JWT session tokens and user profile linking.

---

## 4. CURRENT DATABASE STATUS

- **Engine:** SQLite 3 (`Main App/data.db`) via Python standard library `sqlite3`.
- **Tables:**
  - `users (id INTEGER PRIMARY KEY, name TEXT UNIQUE, created_at TIMESTAMP)`
  - `exercises (id INTEGER PRIMARY KEY, user_id INTEGER, exercise_name TEXT, reps INTEGER, sets INTEGER, time REAL, created_at TIMESTAMP)`
- **Cloud Readiness:** `services/persistence/exercise_repository.py` has basic fallback checks for `st.secrets["SUPABASE_URL"]`, but full schema migrations, RLS policies, and relationship models are missing.

---

## 5. CURRENT GROQ STATUS

- **Integration:** Initialized in `main.py` via `groq.Groq(api_key=api_key)`.
- **Model:** `llama-3.3-70b-versatile`.
- **Resilience:** Wrapped in `try...except` and delegates to `_deterministic_fallback` in `LLMCoach`. The app does NOT crash when the API key is missing or invalid.
- **Gap:** No conversational memory or RAG pipeline querying the user's historical workout database.

---

## 6. CURRENT TTS STATUS

- **Engine:** Google Text-to-Speech (`gtts.gTTS`) in `services/coaching/tts.py`.
- **Playback:** Converts text to MP3 bytes in-memory and triggers playback via hidden `<audio autoplay>` tag.
- **Limitations:** Requires active internet connection; introduces latency; repeated phrases ("Keep your back straight") re-generate repeatedly rather than playing from a cached byte buffer.

---

## 7. CURRENT WORKOUT HISTORY STATUS

- **Aggregation:** `main.py` queries `get_users_exercises(user_id)` and aggregates by `(Exercise, Date)`.
- **UI:** Displays 4 KPI metric cards, a Streamlit bar chart of volume, a paginated data table, and a CSV download button (`adhi_gym_workout_history.csv`).
- **Limitation:** Does not track set-by-set breakdown, timestamps, form violation counts, or AI coach summaries.

---

## 8. CURRENT VIDEO PIPELINE

- **Ingestion:** WebRTC stream via `streamlit-webrtc` (H.264/VP8 video packets).
- **Processing:** `VideoProcessorClass` in `services/vision/exercise_video_processor.py`.
- **Color Format:** Inbound BGR converted to RGB (`cv2.COLOR_BGR2RGB`) for MediaPipe `mp.Image`.
- **Inference:** MediaPipe Tasks PoseLandmarker running synchronously inside the WebRTC frame callback thread.
- **Annotation:** OpenCV overlays bounding boxes, landmarks, angles, and feedback text directly on the frame buffer.
- **Privacy Compliance:** Frames are processed transiently in memory; no video files or user image streams are written to disk.

---

## 9. SUPPORTED EXERCISES

| Exercise | Primary Joint Angle | Form Metric 1 | Form Metric 2 | Rep Transitions |
| :--- | :--- | :--- | :--- | :--- |
| **Biceps Curl** | Elbow ($\ge 160^\circ \to \le 50^\circ$) | Elbow Drift ($\le 0.06$) | Torso Swing ($\le 15^\circ$) | DOWN $\to$ UP $\to$ DOWN |
| **Squat** | Knee ($\ge 160^\circ \to \le 100^\circ$) | Depth (Deep / Parallel / High) | Back Angle ($\ge 130^\circ$) | UP $\to$ DOWN $\to$ UP |
| **Push-up** | Elbow ($> 160^\circ \to < 90^\circ$) | Collinearity ($> 160^\circ$) | Hip Sag / Pike ($\Delta y \le 0.08$) | UP $\to$ DOWN $\to$ UP |
| **Shoulder Press** | Elbow ($< 90^\circ \to > 160^\circ$) | Full Arm Extension | Lumbar Arch Status | DOWN $\to$ UP $\to$ DOWN |
| **Lunges** | Bilateral Knee ($< 100^\circ$) | Dynamic Front Leg Selection | Torso Balance ($|x_{sh} - x_{hip}| \le 0.10$) | UP $\to$ DOWN $\to$ UP |

---

## 10. CURRENT DEPLOYMENT STATUS

- **Local:** Fully functional on `http://localhost:8501`.
- **Cloud Prep:** Model paths use relative `Path(__file__)` resolution.
- **Requirements:** `requirements.txt` contains clean, pinned dependencies compatible with Python 3.12.
- **Cloud Target:** Streamlit Community Cloud (App) + GitHub Pages (Landing Page) + Supabase (Database & Auth) + Groq (LLM).

---

## 11. SECURITY ISSUES

- **Unauthenticated Database Access:** Local SQLite database allows any user to query any `user_id` if they manipulate session state.
- **No RLS (Row Level Security):** Data is not yet protected by Supabase RLS policies.
- **No Secrets Committed:** `.gitignore` properly includes `.env`, `data.db`, and `.streamlit/secrets.toml`. `.env.example` must be supplied.

---

## 12. FAKE / UNSUPPORTED METRICS

- **Audit Finding:** Landing page previously claimed "100ms latency" and "95% accuracy".
- **Remediation:** Falsified claims removed. Replaced with truthful technical descriptors:
  - `<45ms Pipeline Latency` (measured on modern CPU via MediaPipe C++ backend)
  - `5 Core Exercises`
  - `33 Pts 3D Pose Tracking`
- **Future Guarantee:** All production latency figures will be derived strictly from `scripts/benchmark_vision.py`.

---

## 13. THIRD-PARTY PERSONAL DETAILS

- **Attribution Cleanup:**
  - Removed all personal links, emails, and social profiles of reference author (Prince Khunt) from `LandingPage/index.html` and `services/auth/login_wall.py`.
  - Academic attribution and reference repository link properly documented in `ACKNOWLEDGMENTS.md`.
  - Application rebranding strictly set to **Adhi's AI Gym Coach**.

---

## 14. MISSING FEATURES TO COMPLETE SPECIFICATION

1. Supabase PostgreSQL schema with 5 relational tables (`profiles`, `workout_sessions`, `exercise_sets`, `form_events`, `workout_summaries`).
2. Production Supabase Auth with RLS policies isolating user records.
3. Multi-page navigation (Dashboard, Start Workout, Live Workout, History, Progress Analytics, Ask Adhi Coach, Profile).
4. Dedicated "Ask Adhi Coach" RAG chatbot querying historical performance data.
5. Voice engine with audio phrase caching and client-side SpeechSynthesis.
6. Post-workout AI coaching summary generation.
7. Vision benchmark suite (`scripts/benchmark_vision.py`) generating `docs/PERFORMANCE.md`.
8. Complete technical documentation suite in `docs/`.
