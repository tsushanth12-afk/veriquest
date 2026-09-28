-- ==========================================================================
-- VeriQuest Migration 003 — Canonical Submission Status Contract
--
-- Drops and recreates the valid_submission_status CHECK constraint on public.submissions
-- to include 'evaluator_not_configured' alongside canonical lifecycle and grading statuses.
-- Strictly excludes retired/alias values ('failed').
-- ==========================================================================

ALTER TABLE public.submissions
    DROP CONSTRAINT IF EXISTS valid_submission_status;

ALTER TABLE public.submissions
    ADD CONSTRAINT valid_submission_status CHECK (status IN (
        'queued',
        'compiling',
        'running',
        'accepted',
        'wrong_answer',
        'compilation_error',
        'simulation_error',
        'evaluator_not_configured',
        'timeout',
        'resource_limit',
        'system_error',
        'cancelled'
    ));
