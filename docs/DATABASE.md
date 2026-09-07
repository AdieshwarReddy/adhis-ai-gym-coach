# Database Architecture & Schema Specification

**System:** Adhi's AI Gym Coach  
**Database Engine:** Supabase PostgreSQL 15+ (with SQLite 3 local offline fallback)  
**Security Model:** Row Level Security (RLS) with JWT-based tenant isolation  

---

## 1. Entity-Relationship Diagram (ERD)

```
       auth.users (Supabase Auth)
           │
           │ 1:1
           ▼
     public.profiles
           │
           │ 1:N
           ▼
public.workout_sessions ◄───────────────┐
     │                  │               │
     │ 1:N              │ 1:N           │ 1:1
     ▼                  ▼               ▼
public.exercise_sets  public.form_events  public.workout_summaries
```

---

## 2. Table Schemas

### 2.1 `profiles`
Stores user profile information associated with their Supabase authentication ID.
- `id (UUID, PK)`: Unique profile identifier.
- `auth_user_id (UUID, Unique, FK -> auth.users.id)`: Links directly to authenticated user.
- `display_name (TEXT)`: User's chosen public name.
- `age (INTEGER, Nullable)`: Optional fitness demographic.
- `height_cm (NUMERIC, Nullable)`: Optional biometric tracking.
- `experience_level (TEXT)`: 'Beginner', 'Intermediate', 'Advanced'.
- `created_at (TIMESTAMPTZ)`: Account creation timestamp.
- `updated_at (TIMESTAMPTZ)`: Last profile modification.

### 2.2 `workout_sessions`
Tracks individual training workouts.
- `id (UUID, PK)`: Unique session identifier.
- `user_id (UUID, FK -> profiles.id)`: Owner of the workout session.
- `started_at (TIMESTAMPTZ)`: Session start timestamp.
- `completed_at (TIMESTAMPTZ, Nullable)`: Session conclusion timestamp.
- `duration_seconds (INTEGER)`: Total elapsed training time.
- `status (TEXT)`: `'in_progress'`, `'completed'`, or `'aborted'`.
- `created_at (TIMESTAMPTZ)`: Record creation timestamp.

### 2.3 `exercise_sets`
Granular record of each completed or attempted set within a session.
- `id (UUID, PK)`: Unique set record.
- `session_id (UUID, FK -> workout_sessions.id)`: Parent session.
- `exercise_type (TEXT)`: Name of exercise ('Squats', 'Push-ups', etc.).
- `set_number (INTEGER)`: Ordinal set index (1, 2, 3...).
- `target_reps (INTEGER)`: Planned target reps.
- `completed_reps (INTEGER)`: Number of valid reps detected.
- `started_at (TIMESTAMPTZ)`: Timestamp set began.
- `completed_at (TIMESTAMPTZ)`: Timestamp set finished.

### 2.4 `form_events`
Stores specific form deviations and biomechanical cues with a 2-second cooldown to prevent frame spam.
- `id (UUID, PK)`: Unique event identifier.
- `session_id (UUID, FK -> workout_sessions.id)`: Associated session.
- `exercise_type (TEXT)`: Exercise being performed.
- `event_type (TEXT)`: 'form_flaw', 'milestone', 'safety_alert'.
- `metric_name (TEXT)`: 'elbow_drift', 'hip_sag', 'back_arch', 'depth'.
- `metric_value (FLOAT, Nullable)`: Numerical deviation value.
- `message (TEXT)`: User-facing correction or praise.
- `created_at (TIMESTAMPTZ)`: Exact occurrence timestamp.

### 2.5 `workout_summaries`
High-level summary generated upon session completion for quick dashboard rendering and LLM coach contextual recall.
- `id (UUID, PK)`: Unique summary ID.
- `session_id (UUID, Unique, FK -> workout_sessions.id)`: Unique 1:1 session link.
- `total_reps (INTEGER)`: Aggregate rep count across all sets.
- `completed_sets (INTEGER)`: Total completed sets.
- `duration_seconds (INTEGER)`: Total session duration.
- `coach_summary (TEXT)`: AI-generated post-workout review.
- `created_at (TIMESTAMPTZ)`: Summary generation timestamp.

---

## 3. Row Level Security (RLS) Guarantees

All 5 application tables have RLS strictly enabled:
1. `profiles`: Users can only read, insert, and update rows where `auth_user_id = auth.uid()`.
2. `workout_sessions`: Users can only interact with sessions where `user_id = public.get_my_profile_id()`.
3. `exercise_sets`, `form_events`, `workout_summaries`: Users can only interact with rows belonging to their own `workout_sessions`.

---

## 4. SQLite Offline Fallback Mode
When `SUPABASE_URL` is empty or unreachable:
- The system automatically initializes `Main App/data.db` using SQLite.
- Supports local development, offline workouts, and self-contained testing.
