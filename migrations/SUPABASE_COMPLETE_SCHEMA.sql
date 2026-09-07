-- ============================================================================
-- ADHI'S AI GYM COACH - COMPLETE SUPABASE DATABASE SCHEMA
-- ============================================================================
-- How to apply:
-- 1. Log into your Supabase project dashboard (https://supabase.com/dashboard)
-- 2. Click "SQL Editor" in the left sidebar
-- 3. Click "+ New Query"
-- 4. Paste this ENTIRE file into the editor and click "RUN"
-- ============================================================================

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ────────────────────────────────────────────────────────────────────────────
-- 1. PUBLIC PROFILES TABLE
-- ────────────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS public.profiles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    auth_user_id UUID UNIQUE REFERENCES auth.users(id) ON DELETE CASCADE,
    username TEXT UNIQUE,
    display_name TEXT NOT NULL DEFAULT 'Athlete',
    avatar_url TEXT,
    age INTEGER CHECK (age > 0 AND age < 130),
    height_cm REAL CHECK (height_cm > 0),
    experience_level TEXT DEFAULT 'Beginner' CHECK (experience_level IN ('Beginner', 'Intermediate', 'Advanced')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ────────────────────────────────────────────────────────────────────────────
-- 2. STRENGTH WORKOUT SESSIONS TABLE
-- ────────────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS public.workout_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES public.profiles(id) ON DELETE CASCADE,
    started_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    completed_at TIMESTAMPTZ,
    duration_seconds INTEGER NOT NULL DEFAULT 0,
    status TEXT NOT NULL DEFAULT 'in_progress' CHECK (status IN ('in_progress', 'completed', 'abandoned')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ────────────────────────────────────────────────────────────────────────────
-- 3. EXERCISE SETS TABLE
-- ────────────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS public.exercise_sets (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID NOT NULL REFERENCES public.workout_sessions(id) ON DELETE CASCADE,
    exercise_type TEXT NOT NULL CHECK (exercise_type IN ('Squats', 'Push-ups', 'Biceps Curls (Dumbbell)', 'Shoulder Press', 'Lunges')),
    set_number INTEGER NOT NULL CHECK (set_number > 0),
    target_reps INTEGER NOT NULL DEFAULT 0,
    completed_reps INTEGER NOT NULL DEFAULT 0 CHECK (completed_reps >= 0),
    weight_kg REAL DEFAULT 0,
    completed_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ────────────────────────────────────────────────────────────────────────────
-- 4. FORM EVENTS TABLE (Vision Feedback Logs)
-- ────────────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS public.form_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID NOT NULL REFERENCES public.workout_sessions(id) ON DELETE CASCADE,
    exercise_type TEXT NOT NULL,
    event_type TEXT NOT NULL CHECK (event_type IN ('form_flaw', 'good_rep', 'pause', 'resume')),
    metric_name TEXT NOT NULL,
    metric_value REAL,
    message TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ────────────────────────────────────────────────────────────────────────────
-- 5. WORKOUT SUMMARIES TABLE (AI Coach Feedback)
-- ────────────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS public.workout_summaries (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID UNIQUE NOT NULL REFERENCES public.workout_sessions(id) ON DELETE CASCADE,
    total_reps INTEGER NOT NULL DEFAULT 0,
    completed_sets INTEGER NOT NULL DEFAULT 0,
    duration_seconds INTEGER NOT NULL DEFAULT 0,
    coach_summary TEXT NOT NULL DEFAULT '',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ────────────────────────────────────────────────────────────────────────────
-- 6. CARDIO SESSIONS TABLE (Running & Walking)
-- ────────────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS public.cardio_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES public.profiles(id) ON DELETE CASCADE,
    activity_type TEXT NOT NULL CHECK (activity_type IN ('Running', 'Walking', 'Cycling')),
    started_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    completed_at TIMESTAMPTZ,
    elapsed_seconds INTEGER NOT NULL DEFAULT 0,
    moving_seconds INTEGER NOT NULL DEFAULT 0,
    distance_meters DOUBLE PRECISION NOT NULL DEFAULT 0.0,
    average_speed_kmh DOUBLE PRECISION NOT NULL DEFAULT 0.0,
    average_pace_sec_per_km DOUBLE PRECISION NOT NULL DEFAULT 0.0,
    status TEXT NOT NULL DEFAULT 'in_progress' CHECK (status IN ('in_progress', 'completed', 'abandoned')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ────────────────────────────────────────────────────────────────────────────
-- 7. CARDIO ROUTE POINTS TABLE (GPS Polylines)
-- ────────────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS public.cardio_route_points (
    id BIGSERIAL PRIMARY KEY,
    session_id UUID NOT NULL REFERENCES public.cardio_sessions(id) ON DELETE CASCADE,
    sequence_number INTEGER NOT NULL,
    latitude DOUBLE PRECISION NOT NULL,
    longitude DOUBLE PRECISION NOT NULL,
    accuracy_meters DOUBLE PRECISION,
    speed_mps DOUBLE PRECISION,
    recorded_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ────────────────────────────────────────────────────────────────────────────
-- 8. INDEXES FOR PERFORMANCE
-- ────────────────────────────────────────────────────────────────────────────
CREATE INDEX IF NOT EXISTS idx_workout_sessions_user ON public.workout_sessions(user_id, started_at DESC);
CREATE INDEX IF NOT EXISTS idx_exercise_sets_session ON public.exercise_sets(session_id, set_number ASC);
CREATE INDEX IF NOT EXISTS idx_form_events_session ON public.form_events(session_id, created_at ASC);
CREATE INDEX IF NOT EXISTS idx_cardio_sessions_user ON public.cardio_sessions(user_id, started_at DESC);
CREATE INDEX IF NOT EXISTS idx_cardio_route_points_session ON public.cardio_route_points(session_id, sequence_number ASC);

-- ────────────────────────────────────────────────────────────────────────────
-- 9. ROW LEVEL SECURITY (RLS) POLICIES
-- ────────────────────────────────────────────────────────────────────────────
ALTER TABLE public.profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.workout_sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.exercise_sets ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.form_events ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.workout_summaries ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.cardio_sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.cardio_route_points ENABLE ROW LEVEL SECURITY;

-- Profiles RLS
DROP POLICY IF EXISTS "Users can view own profile" ON public.profiles;
CREATE POLICY "Users can view own profile" ON public.profiles FOR SELECT USING (auth.uid() = auth_user_id);
DROP POLICY IF EXISTS "Users can update own profile" ON public.profiles;
CREATE POLICY "Users can update own profile" ON public.profiles FOR UPDATE USING (auth.uid() = auth_user_id);
DROP POLICY IF EXISTS "Service role can insert profile" ON public.profiles;
CREATE POLICY "Service role can insert profile" ON public.profiles FOR INSERT WITH CHECK (true);

-- Workout Sessions RLS
DROP POLICY IF EXISTS "Users can view own workout sessions" ON public.workout_sessions;
CREATE POLICY "Users can view own workout sessions" ON public.workout_sessions FOR SELECT
    USING (user_id IN (SELECT id FROM public.profiles WHERE auth_user_id = auth.uid()));
DROP POLICY IF EXISTS "Users can insert own workout sessions" ON public.workout_sessions;
CREATE POLICY "Users can insert own workout sessions" ON public.workout_sessions FOR INSERT
    WITH CHECK (user_id IN (SELECT id FROM public.profiles WHERE auth_user_id = auth.uid()));
DROP POLICY IF EXISTS "Users can update own workout sessions" ON public.workout_sessions;
CREATE POLICY "Users can update own workout sessions" ON public.workout_sessions FOR UPDATE
    USING (user_id IN (SELECT id FROM public.profiles WHERE auth_user_id = auth.uid()));

-- Exercise Sets RLS
DROP POLICY IF EXISTS "Users can view own exercise sets" ON public.exercise_sets;
CREATE POLICY "Users can view own exercise sets" ON public.exercise_sets FOR SELECT
    USING (session_id IN (
        SELECT ws.id FROM public.workout_sessions ws
        JOIN public.profiles p ON ws.user_id = p.id
        WHERE p.auth_user_id = auth.uid()
    ));
DROP POLICY IF EXISTS "Users can insert own exercise sets" ON public.exercise_sets;
CREATE POLICY "Users can insert own exercise sets" ON public.exercise_sets FOR INSERT
    WITH CHECK (session_id IN (
        SELECT ws.id FROM public.workout_sessions ws
        JOIN public.profiles p ON ws.user_id = p.id
        WHERE p.auth_user_id = auth.uid()
    ));

-- Form Events RLS
DROP POLICY IF EXISTS "Users can view own form events" ON public.form_events;
CREATE POLICY "Users can view own form events" ON public.form_events FOR SELECT
    USING (session_id IN (
        SELECT ws.id FROM public.workout_sessions ws
        JOIN public.profiles p ON ws.user_id = p.id
        WHERE p.auth_user_id = auth.uid()
    ));
DROP POLICY IF EXISTS "Users can insert own form events" ON public.form_events;
CREATE POLICY "Users can insert own form events" ON public.form_events FOR INSERT
    WITH CHECK (session_id IN (
        SELECT ws.id FROM public.workout_sessions ws
        JOIN public.profiles p ON ws.user_id = p.id
        WHERE p.auth_user_id = auth.uid()
    ));

-- Workout Summaries RLS
DROP POLICY IF EXISTS "Users can view own summaries" ON public.workout_summaries;
CREATE POLICY "Users can view own summaries" ON public.workout_summaries FOR SELECT
    USING (session_id IN (
        SELECT ws.id FROM public.workout_sessions ws
        JOIN public.profiles p ON ws.user_id = p.id
        WHERE p.auth_user_id = auth.uid()
    ));
DROP POLICY IF EXISTS "Users can insert own summaries" ON public.workout_summaries;
CREATE POLICY "Users can insert own summaries" ON public.workout_summaries FOR INSERT
    WITH CHECK (session_id IN (
        SELECT ws.id FROM public.workout_sessions ws
        JOIN public.profiles p ON ws.user_id = p.id
        WHERE p.auth_user_id = auth.uid()
    ));

-- Cardio Sessions RLS
DROP POLICY IF EXISTS "Users can view own cardio sessions" ON public.cardio_sessions;
CREATE POLICY "Users can view own cardio sessions" ON public.cardio_sessions FOR SELECT
    USING (user_id IN (SELECT id FROM public.profiles WHERE auth_user_id = auth.uid()));
DROP POLICY IF EXISTS "Users can insert own cardio sessions" ON public.cardio_sessions;
CREATE POLICY "Users can insert own cardio sessions" ON public.cardio_sessions FOR INSERT
    WITH CHECK (user_id IN (SELECT id FROM public.profiles WHERE auth_user_id = auth.uid()));
DROP POLICY IF EXISTS "Users can update own cardio sessions" ON public.cardio_sessions;
CREATE POLICY "Users can update own cardio sessions" ON public.cardio_sessions FOR UPDATE
    USING (user_id IN (SELECT id FROM public.profiles WHERE auth_user_id = auth.uid()));
DROP POLICY IF EXISTS "Users can delete own cardio sessions" ON public.cardio_sessions;
CREATE POLICY "Users can delete own cardio sessions" ON public.cardio_sessions FOR DELETE
    USING (user_id IN (SELECT id FROM public.profiles WHERE auth_user_id = auth.uid()));

-- Cardio Route Points RLS
DROP POLICY IF EXISTS "Users can view own route points" ON public.cardio_route_points;
CREATE POLICY "Users can view own route points" ON public.cardio_route_points FOR SELECT
    USING (session_id IN (
        SELECT cs.id FROM public.cardio_sessions cs
        JOIN public.profiles p ON cs.user_id = p.id
        WHERE p.auth_user_id = auth.uid()
    ));
DROP POLICY IF EXISTS "Users can insert own route points" ON public.cardio_route_points;
CREATE POLICY "Users can insert own route points" ON public.cardio_route_points FOR INSERT
    WITH CHECK (session_id IN (
        SELECT cs.id FROM public.cardio_sessions cs
        JOIN public.profiles p ON cs.user_id = p.id
        WHERE p.auth_user_id = auth.uid()
    ));
DROP POLICY IF EXISTS "Users can delete own route points" ON public.cardio_route_points;
CREATE POLICY "Users can delete own route points" ON public.cardio_route_points FOR DELETE
    USING (session_id IN (
        SELECT cs.id FROM public.cardio_sessions cs
        JOIN public.profiles p ON cs.user_id = p.id
        WHERE p.auth_user_id = auth.uid()
    ));

-- ────────────────────────────────────────────────────────────────────────────
-- 8. TRANSFORMATIONS TABLE (Before & After, Body Metrics)
-- ────────────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS public.transformations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES public.profiles(id) ON DELETE CASCADE,
    recorded_date DATE NOT NULL DEFAULT CURRENT_DATE,
    weight_kg REAL,
    body_fat_pct REAL,
    chest_cm REAL,
    waist_cm REAL,
    arms_cm REAL,
    notes TEXT,
    before_img_data TEXT,
    after_img_data TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ────────────────────────────────────────────────────────────────────────────
-- 9. INDEXES FOR PERFORMANCE
-- ────────────────────────────────────────────────────────────────────────────
CREATE INDEX IF NOT EXISTS idx_workout_sessions_user ON public.workout_sessions(user_id, started_at DESC);
CREATE INDEX IF NOT EXISTS idx_exercise_sets_session ON public.exercise_sets(session_id, set_number ASC);
CREATE INDEX IF NOT EXISTS idx_form_events_session ON public.form_events(session_id, created_at ASC);
CREATE INDEX IF NOT EXISTS idx_cardio_sessions_user ON public.cardio_sessions(user_id, started_at DESC);
CREATE INDEX IF NOT EXISTS idx_cardio_route_points_session ON public.cardio_route_points(session_id, sequence_number ASC);
CREATE INDEX IF NOT EXISTS idx_transformations_user ON public.transformations(user_id, recorded_date ASC);

-- ────────────────────────────────────────────────────────────────────────────
-- 10. ROW LEVEL SECURITY (RLS) POLICIES
-- ────────────────────────────────────────────────────────────────────────────
ALTER TABLE public.profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.workout_sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.exercise_sets ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.form_events ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.workout_summaries ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.cardio_sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.cardio_route_points ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.transformations ENABLE ROW LEVEL SECURITY;

-- Transformations RLS
DROP POLICY IF EXISTS "Users can view own transformations" ON public.transformations;
CREATE POLICY "Users can view own transformations" ON public.transformations FOR SELECT
    USING (user_id IN (SELECT id FROM public.profiles WHERE auth_user_id = auth.uid()));
DROP POLICY IF EXISTS "Users can insert own transformations" ON public.transformations;
CREATE POLICY "Users can insert own transformations" ON public.transformations FOR INSERT
    WITH CHECK (user_id IN (SELECT id FROM public.profiles WHERE auth_user_id = auth.uid()));
DROP POLICY IF EXISTS "Users can update own transformations" ON public.transformations;
CREATE POLICY "Users can update own transformations" ON public.transformations FOR UPDATE
    USING (user_id IN (SELECT id FROM public.profiles WHERE auth_user_id = auth.uid()));
DROP POLICY IF EXISTS "Users can delete own transformations" ON public.transformations;
CREATE POLICY "Users can delete own transformations" ON public.transformations FOR DELETE
    USING (user_id IN (SELECT id FROM public.profiles WHERE auth_user_id = auth.uid()));

-- ────────────────────────────────────────────────────────────────────────────
-- 11. AUTO-CREATE PROFILE ON AUTH SIGNUP (Trigger)
-- ────────────────────────────────────────────────────────────────────────────
CREATE OR REPLACE FUNCTION public.handle_new_user()
RETURNS TRIGGER AS $$
BEGIN
    INSERT INTO public.profiles (auth_user_id, username, display_name)
    VALUES (
        NEW.id,
        COALESCE(NEW.raw_user_meta_data->>'username', split_part(NEW.email, '@', 1)),
        COALESCE(NEW.raw_user_meta_data->>'display_name', split_part(NEW.email, '@', 1))
    )
    ON CONFLICT (auth_user_id) DO NOTHING;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

DROP TRIGGER IF EXISTS on_auth_user_created ON auth.users;
CREATE TRIGGER on_auth_user_created
    AFTER INSERT ON auth.users
    FOR EACH ROW EXECUTE FUNCTION public.handle_new_user();

