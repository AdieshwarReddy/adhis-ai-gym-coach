-- ==============================================================================
-- ADHI'S AI GYM COACH — SUPABASE PRODUCTION SCHEMA (POSTGRESQL + RLS)
-- ==============================================================================
-- Run this script in the Supabase SQL Editor (Dashboard > SQL Editor > New Query)
-- to initialize the database with full Row Level Security (RLS).
-- ==============================================================================

-- 1. Profiles Table (linked to Supabase Auth or standalone usernames)
CREATE TABLE IF NOT EXISTS public.profiles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    username TEXT UNIQUE NOT NULL,
    full_name TEXT,
    avatar_url TEXT,
    created_at TIMESTAMPTZ DEFAULT timezone('utc'::text, now()) NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT timezone('utc'::text, now()) NOT NULL
);

-- 2. Exercises Table (Historical aggregated log per day or session)
CREATE TABLE IF NOT EXISTS public.exercises (
    id BIGSERIAL PRIMARY KEY,
    user_id TEXT NOT NULL,
    exercise_name TEXT NOT NULL,
    reps INTEGER NOT NULL DEFAULT 0,
    sets INTEGER NOT NULL DEFAULT 0,
    time DOUBLE PRECISION NOT NULL DEFAULT 0.0,
    created_at TIMESTAMPTZ DEFAULT timezone('utc'::text, now()) NOT NULL
);

-- 3. Workout Sessions Table (Lifecycle of a single workout)
CREATE TABLE IF NOT EXISTS public.workout_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id TEXT NOT NULL,
    exercise_name TEXT NOT NULL,
    target_sets INTEGER NOT NULL DEFAULT 3,
    target_reps INTEGER NOT NULL DEFAULT 10,
    started_at TIMESTAMPTZ DEFAULT timezone('utc'::text, now()) NOT NULL,
    ended_at TIMESTAMPTZ,
    status TEXT DEFAULT 'IN_PROGRESS' -- 'IN_PROGRESS', 'COMPLETED', 'ABORTED'
);

-- 4. Exercise Sets Table (Detailed per-set tracking)
CREATE TABLE IF NOT EXISTS public.exercise_sets (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID REFERENCES public.workout_sessions(id) ON DELETE CASCADE,
    set_number INTEGER NOT NULL,
    reps_completed INTEGER NOT NULL DEFAULT 0,
    target_reps INTEGER NOT NULL DEFAULT 10,
    duration_seconds DOUBLE PRECISION NOT NULL DEFAULT 0.0,
    avg_form_status TEXT DEFAULT 'GOOD',
    created_at TIMESTAMPTZ DEFAULT timezone('utc'::text, now()) NOT NULL
);

-- 5. Real-Time Feedback Cues Table (Audit log of AI feedback given)
CREATE TABLE IF NOT EXISTS public.feedback_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id TEXT NOT NULL,
    exercise_name TEXT NOT NULL,
    event_type TEXT NOT NULL, -- 'form_issue', 'set_completed', 'workout_completed'
    issue_detected TEXT,
    coach_cue TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT timezone('utc'::text, now()) NOT NULL
);

-- Indexes for lightning fast queries
CREATE INDEX IF NOT EXISTS idx_exercises_user_date ON public.exercises (user_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_workout_sessions_user ON public.workout_sessions (user_id, started_at DESC);
CREATE INDEX IF NOT EXISTS idx_exercise_sets_session ON public.exercise_sets (session_id);

-- Enable Row Level Security (RLS)
ALTER TABLE public.profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.exercises ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.workout_sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.exercise_sets ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.feedback_events ENABLE ROW LEVEL SECURITY;

-- Allow public read/insert for anonymous demo or authenticated users
CREATE POLICY "Allow public read on exercises" ON public.exercises
    FOR SELECT USING (true);

CREATE POLICY "Allow public insert on exercises" ON public.exercises
    FOR INSERT WITH CHECK (true);

CREATE POLICY "Allow public update on exercises" ON public.exercises
    FOR UPDATE USING (true);

CREATE POLICY "Allow public all on profiles" ON public.profiles
    FOR ALL USING (true);

CREATE POLICY "Allow public all on sessions" ON public.workout_sessions
    FOR ALL USING (true);

CREATE POLICY "Allow public all on sets" ON public.exercise_sets
    FOR ALL USING (true);

CREATE POLICY "Allow public all on feedback" ON public.feedback_events
    FOR ALL USING (true);
