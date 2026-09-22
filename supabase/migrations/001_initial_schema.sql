-- ==========================================================================
-- VeriQuest Database Schema — Full Migration
-- ==========================================================================

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ==========================================================================
-- 1. PROFILES (extends Supabase auth.users)
-- ==========================================================================
CREATE TABLE public.profiles (
    id          UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    username    TEXT UNIQUE NOT NULL,
    display_name TEXT,
    avatar_url  TEXT,
    bio         TEXT DEFAULT '',
    level       INTEGER NOT NULL DEFAULT 1,
    xp          INTEGER NOT NULL DEFAULT 0,
    current_streak  INTEGER NOT NULL DEFAULT 0,
    longest_streak  INTEGER NOT NULL DEFAULT 0,
    total_solved    INTEGER NOT NULL DEFAULT 0,
    easy_solved     INTEGER NOT NULL DEFAULT 0,
    medium_solved   INTEGER NOT NULL DEFAULT 0,
    hard_solved     INTEGER NOT NULL DEFAULT 0,
    total_attempts  INTEGER NOT NULL DEFAULT 0,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT xp_non_negative CHECK (xp >= 0),
    CONSTRAINT level_positive CHECK (level >= 1),
    CONSTRAINT streak_non_negative CHECK (current_streak >= 0 AND longest_streak >= 0)
);

-- Auto-create profile on signup
CREATE OR REPLACE FUNCTION public.handle_new_user()
RETURNS TRIGGER AS $$
BEGIN
    INSERT INTO public.profiles (id, username, display_name)
    VALUES (
        NEW.id,
        COALESCE(NEW.raw_user_meta_data->>'username', split_part(NEW.email, '@', 1)),
        COALESCE(NEW.raw_user_meta_data->>'display_name', split_part(NEW.email, '@', 1))
    );
    RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

CREATE TRIGGER on_auth_user_created
    AFTER INSERT ON auth.users
    FOR EACH ROW EXECUTE FUNCTION public.handle_new_user();

-- ==========================================================================
-- 2. USER ROLES
-- ==========================================================================
CREATE TABLE public.user_roles (
    id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id     UUID NOT NULL REFERENCES public.profiles(id) ON DELETE CASCADE,
    role        TEXT NOT NULL DEFAULT 'student',
    granted_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    granted_by  UUID REFERENCES public.profiles(id),

    CONSTRAINT valid_role CHECK (role IN ('student', 'admin', 'moderator')),
    UNIQUE(user_id, role)
);

-- ==========================================================================
-- 3. CHALLENGES (public metadata)
-- ==========================================================================
CREATE TABLE public.challenges (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    slug            TEXT UNIQUE NOT NULL,
    title           TEXT NOT NULL,
    description     TEXT NOT NULL DEFAULT '',
    category        TEXT NOT NULL DEFAULT 'Fundamentals',
    difficulty      TEXT NOT NULL DEFAULT 'Easy',
    level_number    INTEGER NOT NULL DEFAULT 1,
    xp_reward       INTEGER NOT NULL DEFAULT 50,
    estimated_minutes INTEGER DEFAULT 15,
    starter_code    TEXT NOT NULL DEFAULT '',
    input_description TEXT DEFAULT '',
    output_description TEXT DEFAULT '',
    constraints     JSONB DEFAULT '[]'::JSONB,
    public_examples JSONB DEFAULT '[]'::JSONB,
    io_pins         JSONB DEFAULT '[]'::JSONB,
    hints           JSONB DEFAULT '[]'::JSONB,
    learning_objective TEXT DEFAULT '',
    is_published    BOOLEAN NOT NULL DEFAULT FALSE,
    is_archived     BOOLEAN NOT NULL DEFAULT FALSE,
    validation_status TEXT NOT NULL DEFAULT 'draft',
    validated_at    TIMESTAMPTZ,
    published_at    TIMESTAMPTZ,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT valid_difficulty CHECK (difficulty IN ('Easy', 'Medium', 'Hard')),
    CONSTRAINT valid_validation_status CHECK (validation_status IN ('draft', 'validating', 'validated', 'validation_failed', 'published', 'archived')),
    CONSTRAINT xp_reward_positive CHECK (xp_reward > 0),
    CONSTRAINT level_number_positive CHECK (level_number >= 1),
    CONSTRAINT published_requires_published_status CHECK (NOT is_published OR validation_status = 'published')
);

CREATE INDEX idx_challenges_slug ON public.challenges(slug);
CREATE INDEX idx_challenges_category ON public.challenges(category);
CREATE INDEX idx_challenges_difficulty ON public.challenges(difficulty);
CREATE INDEX idx_challenges_level ON public.challenges(level_number);
CREATE INDEX idx_challenges_published ON public.challenges(is_published) WHERE is_published = TRUE;

-- ==========================================================================
-- 4. CHALLENGE PREREQUISITES
-- ==========================================================================
CREATE TABLE public.challenge_prerequisites (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    challenge_id    UUID NOT NULL REFERENCES public.challenges(id) ON DELETE CASCADE,
    prerequisite_id UUID NOT NULL REFERENCES public.challenges(id) ON DELETE CASCADE,

    CONSTRAINT no_self_prerequisite CHECK (challenge_id != prerequisite_id),
    UNIQUE(challenge_id, prerequisite_id)
);

-- ==========================================================================
-- 5. PRIVATE CHALLENGE SECRETS (server-only, never exposed to students)
-- ==========================================================================
CREATE SCHEMA IF NOT EXISTS private;

CREATE TABLE private.challenge_secrets (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    challenge_id        UUID UNIQUE NOT NULL REFERENCES public.challenges(id) ON DELETE CASCADE,
    official_solution   TEXT NOT NULL DEFAULT '',
    hidden_testbench    TEXT NOT NULL DEFAULT '',
    evaluator_type      TEXT NOT NULL DEFAULT 'hidden_testbench',
    test_vector_config  JSONB DEFAULT '{}'::JSONB,
    execution_profile   JSONB DEFAULT '{
        "timeout_ms": 5000,
        "memory_mb": 256,
        "cpu_limit": "1.0",
        "pids_limit": 64,
        "max_output_bytes": 65536
    }'::JSONB,
    private_notes       TEXT DEFAULT '',
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT valid_evaluator CHECK (evaluator_type IN ('hidden_testbench', 'reference_differential', 'custom'))
);

-- Invalidate published status if secrets change (forces re-validation before re-publishing)
CREATE OR REPLACE FUNCTION private.invalidate_challenge_on_secret_change()
RETURNS TRIGGER AS $$
BEGIN
    IF (OLD.official_solution IS DISTINCT FROM NEW.official_solution) OR
       (OLD.hidden_testbench IS DISTINCT FROM NEW.hidden_testbench) THEN
        UPDATE public.challenges
        SET is_published = FALSE,
            validation_status = 'draft'
        WHERE id = NEW.challenge_id;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

CREATE TRIGGER on_secret_changed_invalidate
    AFTER UPDATE ON private.challenge_secrets
    FOR EACH ROW EXECUTE FUNCTION private.invalidate_challenge_on_secret_change();

-- ==========================================================================
-- 6. USER CHALLENGE PROGRESS
-- ==========================================================================
CREATE TABLE public.user_challenge_progress (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id             UUID NOT NULL REFERENCES public.profiles(id) ON DELETE CASCADE,
    challenge_id        UUID NOT NULL REFERENCES public.challenges(id) ON DELETE CASCADE,
    status              TEXT NOT NULL DEFAULT 'unlocked',
    attempts            INTEGER NOT NULL DEFAULT 0,
    best_submission_id  UUID,
    completed_at        TIMESTAMPTZ,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT valid_progress_status CHECK (status IN ('locked', 'unlocked', 'in_progress', 'completed')),
    CONSTRAINT attempts_non_negative CHECK (attempts >= 0),
    UNIQUE(user_id, challenge_id)
);

CREATE INDEX idx_progress_user ON public.user_challenge_progress(user_id);
CREATE INDEX idx_progress_challenge ON public.user_challenge_progress(challenge_id);

-- ==========================================================================
-- 7. SUBMISSIONS
-- ==========================================================================
CREATE TABLE public.submissions (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id         UUID NOT NULL REFERENCES public.profiles(id) ON DELETE CASCADE,
    challenge_id    UUID NOT NULL REFERENCES public.challenges(id) ON DELETE CASCADE,
    status          TEXT NOT NULL DEFAULT 'queued',
    submitted_code  TEXT NOT NULL,
    idempotency_key TEXT,
    submitted_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    started_at      TIMESTAMPTZ,
    completed_at    TIMESTAMPTZ,
    runtime_ms      INTEGER,
    simulation_ns   INTEGER,
    tests_total     INTEGER DEFAULT 0,
    tests_passed    INTEGER DEFAULT 0,
    tests_failed    INTEGER DEFAULT 0,
    error_code      TEXT,
    public_message  TEXT,
    compiler_output TEXT,
    xp_awarded      INTEGER DEFAULT 0,
    worker_id       TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT valid_submission_status CHECK (status IN (
        'queued', 'compiling', 'running', 'accepted', 'wrong_answer',
        'compilation_error', 'simulation_error', 'timeout',
        'resource_limit', 'system_error', 'cancelled'
    ))
);

CREATE INDEX idx_submissions_user ON public.submissions(user_id);
CREATE INDEX idx_submissions_challenge ON public.submissions(challenge_id);
CREATE INDEX idx_submissions_status ON public.submissions(status);
CREATE INDEX idx_submissions_idempotency ON public.submissions(idempotency_key) WHERE idempotency_key IS NOT NULL;

-- ==========================================================================
-- 8. XP TRANSACTIONS (audit trail)
-- ==========================================================================
CREATE TABLE public.xp_transactions (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id         UUID NOT NULL REFERENCES public.profiles(id) ON DELETE CASCADE,
    challenge_id    UUID REFERENCES public.challenges(id),
    submission_id   UUID REFERENCES public.submissions(id),
    amount          INTEGER NOT NULL,
    reason          TEXT NOT NULL,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT amount_non_zero CHECK (amount != 0)
);

CREATE INDEX idx_xp_transactions_user ON public.xp_transactions(user_id);
-- Idempotency guarantee: A user can only receive XP for a challenge completion once
CREATE UNIQUE INDEX idx_xp_transactions_unique_challenge ON public.xp_transactions(user_id, challenge_id) WHERE challenge_id IS NOT NULL;

-- ==========================================================================
-- 9. QUESTS
-- ==========================================================================
CREATE TABLE public.quests (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    title           TEXT NOT NULL,
    description     TEXT DEFAULT '',
    category        TEXT NOT NULL,
    xp_reward       INTEGER NOT NULL DEFAULT 0,
    is_active       BOOLEAN NOT NULL DEFAULT TRUE,
    sort_order      INTEGER NOT NULL DEFAULT 0,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE public.quest_challenges (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    quest_id        UUID NOT NULL REFERENCES public.quests(id) ON DELETE CASCADE,
    challenge_id    UUID NOT NULL REFERENCES public.challenges(id) ON DELETE CASCADE,
    sort_order      INTEGER NOT NULL DEFAULT 0,

    UNIQUE(quest_id, challenge_id)
);

-- ==========================================================================
-- 10. BADGES
-- ==========================================================================
CREATE TABLE public.badges (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name            TEXT UNIQUE NOT NULL,
    description     TEXT DEFAULT '',
    category        TEXT NOT NULL DEFAULT 'Logic',
    icon            TEXT NOT NULL DEFAULT 'Award',
    requirement     TEXT DEFAULT '',
    rule_type       TEXT NOT NULL DEFAULT 'manual',
    rule_config     JSONB DEFAULT '{}'::JSONB,
    is_active       BOOLEAN NOT NULL DEFAULT TRUE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT valid_badge_category CHECK (category IN ('Logic', 'Timing', 'Consistency', 'Synthesis'))
);

CREATE TABLE public.user_badges (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id         UUID NOT NULL REFERENCES public.profiles(id) ON DELETE CASCADE,
    badge_id        UUID NOT NULL REFERENCES public.badges(id) ON DELETE CASCADE,
    unlocked_at     TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    UNIQUE(user_id, badge_id)
);

-- ==========================================================================
-- 11. STREAK ACTIVITY
-- ==========================================================================
CREATE TABLE public.streak_activity (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id         UUID NOT NULL REFERENCES public.profiles(id) ON DELETE CASCADE,
    activity_date   DATE NOT NULL,
    activity_type   TEXT NOT NULL DEFAULT 'submission',
    activity_count  INTEGER NOT NULL DEFAULT 1,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    UNIQUE(user_id, activity_date)
);

CREATE INDEX idx_streak_user_date ON public.streak_activity(user_id, activity_date DESC);

-- ==========================================================================
-- 12. ADMIN AUDIT LOG
-- ==========================================================================
CREATE TABLE public.admin_audit_log (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    admin_user_id   UUID NOT NULL REFERENCES public.profiles(id),
    action          TEXT NOT NULL,
    target_type     TEXT NOT NULL,
    target_id       UUID,
    details         JSONB DEFAULT '{}'::JSONB,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_audit_admin ON public.admin_audit_log(admin_user_id);
CREATE INDEX idx_audit_created ON public.admin_audit_log(created_at DESC);

-- ==========================================================================
-- 13. ROW LEVEL SECURITY
-- ==========================================================================

-- Profiles: users can read all, update only own (non-server fields)
ALTER TABLE public.profiles ENABLE ROW LEVEL SECURITY;

CREATE POLICY "profiles_select_all" ON public.profiles
    FOR SELECT USING (true);

CREATE POLICY "profiles_update_own" ON public.profiles
    FOR UPDATE USING (auth.uid() = id)
    WITH CHECK (auth.uid() = id);

-- Challenges: anyone can read published
ALTER TABLE public.challenges ENABLE ROW LEVEL SECURITY;

CREATE POLICY "challenges_select_published" ON public.challenges
    FOR SELECT USING (is_published = TRUE);

-- Submissions: users can read/insert own
ALTER TABLE public.submissions ENABLE ROW LEVEL SECURITY;

CREATE POLICY "submissions_select_own" ON public.submissions
    FOR SELECT USING (auth.uid() = user_id);

CREATE POLICY "submissions_insert_own" ON public.submissions
    FOR INSERT WITH CHECK (auth.uid() = user_id);

-- Progress: users can read own
ALTER TABLE public.user_challenge_progress ENABLE ROW LEVEL SECURITY;

CREATE POLICY "progress_select_own" ON public.user_challenge_progress
    FOR SELECT USING (auth.uid() = user_id);

-- XP Transactions: users can read own
ALTER TABLE public.xp_transactions ENABLE ROW LEVEL SECURITY;

CREATE POLICY "xp_select_own" ON public.xp_transactions
    FOR SELECT USING (auth.uid() = user_id);

-- Quests: public read
ALTER TABLE public.quests ENABLE ROW LEVEL SECURITY;
CREATE POLICY "quests_select_all" ON public.quests FOR SELECT USING (is_active = TRUE);

-- Quest Challenges: public read
ALTER TABLE public.quest_challenges ENABLE ROW LEVEL SECURITY;
CREATE POLICY "quest_challenges_select_all" ON public.quest_challenges FOR SELECT USING (true);

-- Badges: public read
ALTER TABLE public.badges ENABLE ROW LEVEL SECURITY;
CREATE POLICY "badges_select_all" ON public.badges FOR SELECT USING (is_active = TRUE);

-- User Badges: users can read own
ALTER TABLE public.user_badges ENABLE ROW LEVEL SECURITY;
CREATE POLICY "user_badges_select_own" ON public.user_badges
    FOR SELECT USING (auth.uid() = user_id);

-- Streak Activity: users can read own
ALTER TABLE public.streak_activity ENABLE ROW LEVEL SECURITY;
CREATE POLICY "streak_select_own" ON public.streak_activity
    FOR SELECT USING (auth.uid() = user_id);

-- Roles: users can read own
ALTER TABLE public.user_roles ENABLE ROW LEVEL SECURITY;
CREATE POLICY "roles_select_own" ON public.user_roles
    FOR SELECT USING (auth.uid() = user_id);

-- Admin Audit: no public access (backend service key only)
ALTER TABLE public.admin_audit_log ENABLE ROW LEVEL SECURITY;

-- ==========================================================================
-- 14. UPDATED_AT TRIGGER
-- ==========================================================================
CREATE OR REPLACE FUNCTION public.update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER set_updated_at_profiles
    BEFORE UPDATE ON public.profiles
    FOR EACH ROW EXECUTE FUNCTION public.update_updated_at();

CREATE TRIGGER set_updated_at_challenges
    BEFORE UPDATE ON public.challenges
    FOR EACH ROW EXECUTE FUNCTION public.update_updated_at();

CREATE TRIGGER set_updated_at_progress
    BEFORE UPDATE ON public.user_challenge_progress
    FOR EACH ROW EXECUTE FUNCTION public.update_updated_at();

CREATE TRIGGER set_updated_at_secrets
    BEFORE UPDATE ON private.challenge_secrets
    FOR EACH ROW EXECUTE FUNCTION public.update_updated_at();

CREATE TRIGGER set_updated_at_quests
    BEFORE UPDATE ON public.quests
    FOR EACH ROW EXECUTE FUNCTION public.update_updated_at();
