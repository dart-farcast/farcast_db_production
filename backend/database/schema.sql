-- ==============================================================================
-- FarCast DB v2 — Supabase Cloud PostgreSQL Master DDL Schema
-- Execute this SQL script in the Supabase SQL Editor (https://supabase.com)
-- ==============================================================================

-- 1. Users Table (Authentication, Whitelist Status & RBAC Study Access)
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    full_name VARCHAR(255),
    password_hash TEXT NOT NULL,
    role VARCHAR(50) NOT NULL DEFAULT 'user',
    is_whitelisted BOOLEAN NOT NULL DEFAULT FALSE,
    allowed_studies TEXT NOT NULL DEFAULT '*',
    allowed_samples TEXT NOT NULL DEFAULT '*',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    last_login TIMESTAMP WITH TIME ZONE
);

CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
CREATE INDEX IF NOT EXISTS idx_users_whitelisted ON users(is_whitelisted);

-- 2. Whitelisted Emails & Domain Rules
CREATE TABLE IF NOT EXISTS whitelisted_emails (
    id SERIAL PRIMARY KEY,
    pattern VARCHAR(255) UNIQUE NOT NULL,
    added_by VARCHAR(255) DEFAULT 'System',
    added_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    notes TEXT
);

CREATE INDEX IF NOT EXISTS idx_whitelist_pattern ON whitelisted_emails(pattern);

-- 3. Security Audit Logs
CREATE TABLE IF NOT EXISTS audit_logs (
    id SERIAL PRIMARY KEY,
    actor_email VARCHAR(255),
    action VARCHAR(100) NOT NULL,
    details TEXT,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_audit_timestamp ON audit_logs(timestamp DESC);

-- 4. Sample Metadata Table
CREATE TABLE IF NOT EXISTS metadata (
    sample_id VARCHAR(100) PRIMARY KEY,
    cancer_type VARCHAR(100),
    tumor_site VARCHAR(100),
    study VARCHAR(100),
    project_id VARCHAR(100),
    hospital VARCHAR(100),
    "Platform_Response" VARCHAR(100) DEFAULT ''
);

CREATE INDEX IF NOT EXISTS idx_meta_cancertype ON metadata(cancer_type);
CREATE INDEX IF NOT EXISTS idx_meta_study ON metadata(study);

-- 5. Arm & Treatment Overlay Table
CREATE TABLE IF NOT EXISTS overlay (
    id SERIAL PRIMARY KEY,
    sample_id VARCHAR(100) NOT NULL,
    arm_code VARCHAR(100),
    drug VARCHAR(255),
    position INT
);

CREATE INDEX IF NOT EXISTS idx_overlay_sid ON overlay(sample_id);
CREATE INDEX IF NOT EXISTS idx_overlay_drug ON overlay(drug);

-- 6. Flow Cytometry Assay Table
CREATE TABLE IF NOT EXISTS assay_flow_cytometry (
    "Sample_ID" TEXT,
    "Name" TEXT,
    "Study" TEXT,
    "Arm" TEXT,
    "Location" TEXT,
    "Full_Path" TEXT
);

CREATE INDEX IF NOT EXISTS idx_assay_flow_sample_id ON assay_flow_cytometry ("Sample_ID");
CREATE INDEX IF NOT EXISTS idx_assay_flow_arm ON assay_flow_cytometry ("Arm");
CREATE INDEX IF NOT EXISTS idx_assay_flow_study ON assay_flow_cytometry ("Study");

-- Seed Initial Default Whitelist Rules & Seed Admin
INSERT INTO whitelisted_emails (pattern, notes) 
VALUES 
    ('admin@farcastbio.com', 'Default Admin Email'),
    ('@farcastbio.com', 'FarCast Bio Company Domain')
ON CONFLICT (pattern) DO NOTHING;

-- ==============================================================================
-- Performance Indexes (added 2026-11-23)
-- Run these in Supabase SQL Editor to activate fast-path search.
-- ==============================================================================

-- 1. GIN full-text search on metadata: enables fast fuzzy/keyword search
--    NOTE: live table uses mixed-case quoted column names (written by pandas to_sql).
CREATE INDEX IF NOT EXISTS idx_meta_fts ON metadata USING GIN (
    to_tsvector(
        'english',
        coalesce("Sample_ID",  '') || ' ' ||
        coalesce("CancerType", '') || ' ' ||
        coalesce("TumorSite",  '') || ' ' ||
        coalesce("Hospital",   '') || ' ' ||
        coalesce("Study",      '')
    )
);

-- 2. Composite index for the most common filter combo (Study + CancerType)
CREATE INDEX IF NOT EXISTS idx_meta_study_cancer ON metadata("Study", "CancerType");

-- 3. Case-insensitive drug search on overlay (avoids full scans for drug lookups)
CREATE INDEX IF NOT EXISTS idx_overlay_drug_lower ON overlay(lower(drug));

-- 4. Partial index on users: only active whitelisted users are queried on every request
ALTER TABLE users ADD COLUMN IF NOT EXISTS is_active BOOLEAN NOT NULL DEFAULT TRUE;
CREATE INDEX IF NOT EXISTS idx_users_active_whitelisted
    ON users(email)
    WHERE is_whitelisted = TRUE AND is_active = TRUE;

-- HOW TO USE the FTS index in queries:
-- SELECT * FROM metadata
-- WHERE to_tsvector('english', coalesce("Sample_ID",'') || ' ' || coalesce("CancerType",''))
--       @@ plainto_tsquery('english', 'lung adenocarcinoma');

