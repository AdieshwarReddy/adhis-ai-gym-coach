-- ============================================================================
-- ADHI'S AI GYM COACH - TRANSFORMATIONS & PROGRESS PHOTOS SCHEMA
-- ============================================================================

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

-- Index for efficient user history lookup
CREATE INDEX IF NOT EXISTS idx_transformations_user ON public.transformations(user_id, recorded_date ASC);

-- Row Level Security (RLS)
ALTER TABLE public.transformations ENABLE ROW LEVEL SECURITY;

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
