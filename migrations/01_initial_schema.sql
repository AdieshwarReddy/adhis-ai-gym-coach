-- ============================================================
-- ADHI'S AI GYM COACH — SUPABASE POSTGRESQL SCHEMA MIGRATION
-- Migration: 01_initial_schema.sql
-- Description: Core schema with Profiles, Workout Sessions, Sets,
--              Form Events, Summaries, and Row Level Security (RLS)
-- ============================================================

-- Enable UUID extension if not already enabled
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ------------------------------------------------------------
-- 1. PROFILES TABLE
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.profiles (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    auth_user_id UUID UNIQUE NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    display_name TEXT NOT NULL,
    age INTEGER,
    height_cm NUMERIC,
    experience_level TEXT DEFAULT 'Beginner',
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

-- ------------------------------------------------------------
-- 2. WORKOUT SESSIONS TABLE
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.workout_sessions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES public.profiles(id) ON DELETE CASCADE,
    started_at TIMESTAMPTZ DEFAULT now(),
    completed_at TIMESTAMPTZ,
    duration_seconds INTEGER DEFAULT 0,
    status TEXT DEFAULT 'in_progress', -- 'in_progress', 'completed', 'aborted'
    created_at TIMESTAMPTZ DEFAULT now()
);

-- ------------------------------------------------------------
-- 3. EXERCISE SETS TABLE
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.exercise_sets (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    session_id UUID NOT NULL REFERENCES public.workout_sessions(id) ON DELETE CASCADE,
    exercise_type TEXT NOT NULL,
    set_number INTEGER NOT NULL,
    target_reps INTEGER NOT NULL,
    completed_reps INTEGER DEFAULT 0,
    started_at TIMESTAMPTZ DEFAULT now(),
    completed_at TIMESTAMPTZ
);

-- ------------------------------------------------------------
-- 4. FORM EVENTS TABLE (Deduplicated with Cooldown)
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.form_events (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    session_id UUID NOT NULL REFERENCES public.workout_sessions(id) ON DELETE CASCADE,
    exercise_type TEXT NOT NULL,
    event_type TEXT NOT NULL, -- e.g. 'form_flaw', 'milestone', 'depth_warning'
    metric_name TEXT,         -- e.g. 'elbow_drift', 'hip_sag', 'back_arch'
    metric_value FLOAT,
    message TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT now()
);

-- ------------------------------------------------------------
-- 5. WORKOUT SUMMARIES TABLE
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.workout_summaries (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    session_id UUID UNIQUE NOT NULL REFERENCES public.workout_sessions(id) ON DELETE CASCADE,
    total_reps INTEGER DEFAULT 0,
    completed_sets INTEGER DEFAULT 0,
    duration_seconds INTEGER DEFAULT 0,
    coach_summary TEXT,
    created_at TIMESTAMPTZ DEFAULT now()
);

-- ------------------------------------------------------------
-- INDEXES FOR FAST QUERYING
-- ------------------------------------------------------------
CREATE INDEX IF NOT EXISTS idx_profiles_auth_user_id ON public.profiles(auth_user_id);
CREATE INDEX IF NOT EXISTS idx_workout_sessions_user_id ON public.workout_sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_exercise_sets_session_id ON public.exercise_sets(session_id);
CREATE INDEX IF NOT EXISTS idx_form_events_session_id ON public.form_events(session_id);
CREATE INDEX IF NOT EXISTS idx_workout_summaries_session_id ON public.workout_summaries(session_id);

-- ============================================================
-- ROW LEVEL SECURITY (RLS) POLICIES
-- Strict Isolation: User A cannot read or write User B's records
-- ============================================================

ALTER TABLE public.profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.workout_sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.exercise_sets ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.form_events ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.workout_summaries ENABLE ROW LEVEL SECURITY;

-- Helper function: get current profile id from auth.uid()
CREATE OR REPLACE FUNCTION public.get_my_profile_id()
RETURNS UUID AS $$
    SELECT id FROM public.profiles WHERE auth_user_id = auth.uid() LIMIT 1;
$$ LANGUAGE sql STABLE SECURITY DEFINER;

-- 1. Profiles Policies
CREATE POLICY "Users can view own profile"
    ON public.profiles FOR SELECT
    USING (auth_user_id = auth.uid());

CREATE POLICY "Users can insert own profile"
    ON public.profiles FOR INSERT
    WITH CHECK (auth_user_id = auth.uid());

CREATE POLICY "Users can update own profile"
    ON public.profiles FOR UPDATE
    USING (auth_user_id = auth.uid());

-- 2. Workout Sessions Policies
CREATE POLICY "Users can view own workout sessions"
    ON public.workout_sessions FOR SELECT
    USING (user_id = public.get_my_profile_id());

CREATE POLICY "Users can insert own workout sessions"
    ON public.workout_sessions FOR INSERT
    WITH CHECK (user_id = public.get_my_profile_id());

CREATE POLICY "Users can update own workout sessions"
    ON public.workout_sessions FOR UPDATE
    USING (user_id = public.get_my_profile_id());

-- 3. Exercise Sets Policies
CREATE POLICY "Users can view own exercise sets"
    ON public.exercise_sets FOR SELECT
    USING (session_id IN (
        SELECT id FROM public.workout_sessions WHERE user_id = public.get_my_profile_id()
    ));

CREATE POLICY "Users can insert own exercise sets"
    ON public.exercise_sets FOR INSERT
    WITH CHECK (session_id IN (
        SELECT id FROM public.workout_sessions WHERE user_id = public.get_my_profile_id()
    ));

-- 4. Form Events Policies
CREATE POLICY "Users can view own form events"
    ON public.form_events FOR SELECT
    USING (session_id IN (
        SELECT id FROM public.workout_sessions WHERE user_id = public.get_my_profile_id()
    ));

CREATE POLICY "Users can insert own form events"
    ON public.form_events FOR INSERT
    WITH CHECK (session_id IN (
        SELECT id FROM public.workout_sessions WHERE user_id = public.get_my_profile_id()
    ));

-- 5. Workout Summaries Policies
CREATE POLICY "Users can view own workout summaries"
    ON public.workout_summaries FOR SELECT
    USING (session_id IN (
        SELECT id FROM public.workout_sessions WHERE user_id = public.get_my_profile_id()
    ));

CREATE POLICY "Users can insert own workout summaries"
    ON public.workout_summaries FOR INSERT
    WITH CHECK (session_id IN (
        SELECT id FROM public.workout_sessions WHERE user_id = public.get_my_profile_id()
    ));

-- ------------------------------------------------------------
-- AUTOMATIC PROFILE CREATION TRIGGER (ON SIGNUP)
-- ------------------------------------------------------------
CREATE OR REPLACE FUNCTION public.handle_new_user()
RETURNS TRIGGER AS $$
BEGIN
    INSERT INTO public.profiles (auth_user_id, display_name)
    VALUES (
        NEW.id,
        COALESCE(NEW.raw_user_meta_data->>'display_name', split_part(NEW.email, '@', 1))
    );
    RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Trigger to automatically populate public.profiles when auth.users row is created
DROP TRIGGER IF EXISTS on_auth_user_created ON auth.users;
CREATE TRIGGER on_auth_user_created
    AFTER INSERT ON auth.users
    FOR EACH ROW EXECUTE FUNCTION public.handle_new_user();
