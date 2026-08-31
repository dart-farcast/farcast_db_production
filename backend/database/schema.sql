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
    hospital VARCHAR(100)
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

-- Seed Initial Default Whitelist Rules & Seed Admin
INSERT INTO whitelisted_emails (pattern, notes) 
VALUES 
    ('admin@farcastbio.com', 'Default Admin Email'),
    ('@farcastbio.com', 'FarCast Bio Company Domain')
ON CONFLICT (pattern) DO NOTHING;
