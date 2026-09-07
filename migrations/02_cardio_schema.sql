-- ============================================================================
-- 02_cardio_schema.sql
-- Adhi's AI Gym Coach: Cardio / Running & Route Tracking Schema
-- Engine: Supabase PostgreSQL 15+ with Row Level Security (RLS)
-- ============================================================================

-- 1. Cardio Sessions Table
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

-- 2. Cardio Route Points (GPS Trail)
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

-- 3. Indexes for fast route queries
CREATE INDEX IF NOT EXISTS idx_cardio_sessions_user ON public.cardio_sessions(user_id, started_at DESC);
CREATE INDEX IF NOT EXISTS idx_cardio_route_points_session ON public.cardio_route_points(session_id, sequence_number ASC);

-- 4. Enable Row Level Security
ALTER TABLE public.cardio_sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.cardio_route_points ENABLE ROW LEVEL SECURITY;

-- 5. RLS Policies (Users can only read and modify their own sessions and routes)
DROP POLICY IF EXISTS "Users can view own cardio sessions" ON public.cardio_sessions;
CREATE POLICY "Users can view own cardio sessions"
    ON public.cardio_sessions FOR SELECT
    USING (user_id IN (SELECT id FROM public.profiles WHERE auth_user_id = auth.uid()));

DROP POLICY IF EXISTS "Users can insert own cardio sessions" ON public.cardio_sessions;
CREATE POLICY "Users can insert own cardio sessions"
    ON public.cardio_sessions FOR INSERT
    WITH CHECK (user_id IN (SELECT id FROM public.profiles WHERE auth_user_id = auth.uid()));

DROP POLICY IF EXISTS "Users can update own cardio sessions" ON public.cardio_sessions;
CREATE POLICY "Users can update own cardio sessions"
    ON public.cardio_sessions FOR UPDATE
    USING (user_id IN (SELECT id FROM public.profiles WHERE auth_user_id = auth.uid()));

DROP POLICY IF EXISTS "Users can delete own cardio sessions" ON public.cardio_sessions;
CREATE POLICY "Users can delete own cardio sessions"
    ON public.cardio_sessions FOR DELETE
    USING (user_id IN (SELECT id FROM public.profiles WHERE auth_user_id = auth.uid()));

DROP POLICY IF EXISTS "Users can view own route points" ON public.cardio_route_points;
CREATE POLICY "Users can view own route points"
    ON public.cardio_route_points FOR SELECT
    USING (session_id IN (
        SELECT cs.id FROM public.cardio_sessions cs
        JOIN public.profiles p ON cs.user_id = p.id
        WHERE p.auth_user_id = auth.uid()
    ));

DROP POLICY IF EXISTS "Users can insert own route points" ON public.cardio_route_points;
CREATE POLICY "Users can insert own route points"
    ON public.cardio_route_points FOR INSERT
    WITH CHECK (session_id IN (
        SELECT cs.id FROM public.cardio_sessions cs
        JOIN public.profiles p ON cs.user_id = p.id
        WHERE p.auth_user_id = auth.uid()
    ));

DROP POLICY IF EXISTS "Users can delete own route points" ON public.cardio_route_points;
CREATE POLICY "Users can delete own route points"
    ON public.cardio_route_points FOR DELETE
    USING (session_id IN (
        SELECT cs.id FROM public.cardio_sessions cs
        JOIN public.profiles p ON cs.user_id = p.id
        WHERE p.auth_user_id = auth.uid()
    ));
