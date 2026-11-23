-- ==============================================================================
-- FarCast DB v2 — Migration 001: Performance Indexes
-- Run this in: Supabase Dashboard → SQL Editor → New Query → Run
-- Date: 2026-11-23
--
-- NOTE: The live metadata table uses mixed-case quoted column names
--       ("Sample_ID", "CancerType", "TumorSite", "Study", "Hospital")
--       as written by pandas to_sql() during ingestion. All references
--       below use double-quotes to match the actual Supabase schema.
-- ==============================================================================

-- 1. GIN Full-Text Search index on metadata
--    Enables fast keyword/fuzzy search across Sample_ID, CancerType,
--    TumorSite, Hospital and Study in a single index scan.
CREATE INDEX IF NOT EXISTS idx_meta_fts ON metadata USING GIN (
    to_tsvector(
        'english',
        coalesce("Sample_ID",   '') || ' ' ||
        coalesce("CancerType",  '') || ' ' ||
        coalesce("TumorSite",   '') || ' ' ||
        coalesce("Hospital",    '') || ' ' ||
        coalesce("Study",       '')
    )
);

-- 2. Composite index — most common dual-filter: Study + CancerType
CREATE INDEX IF NOT EXISTS idx_meta_study_cancer ON metadata("Study", "CancerType");

-- 3. Case-insensitive drug name index on overlay (avoids full scans for drug lookups)
CREATE INDEX IF NOT EXISTS idx_overlay_drug_lower ON overlay(lower(drug));

-- 4. Partial index — only active whitelisted users (checked on every API request).
--    First ensure is_active column exists (safe to run even if it already does):
ALTER TABLE users ADD COLUMN IF NOT EXISTS is_active BOOLEAN NOT NULL DEFAULT TRUE;

CREATE INDEX IF NOT EXISTS idx_users_active_whitelisted
    ON users(email)
    WHERE is_whitelisted = TRUE AND is_active = TRUE;

-- ── Verify all 4 indexes were created successfully ───────────────────────────
SELECT indexname, tablename, indexdef
FROM pg_indexes
WHERE indexname IN (
    'idx_meta_fts',
    'idx_meta_study_cancer',
    'idx_overlay_drug_lower',
    'idx_users_active_whitelisted'
)
ORDER BY tablename, indexname;
