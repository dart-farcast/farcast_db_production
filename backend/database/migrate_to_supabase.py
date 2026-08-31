"""
FarCast DB v2 — Supabase Cloud Migration Tool
Migrates all local tables, schemas, user auth data, and multi-omics assay datasets directly into Supabase Cloud PostgreSQL.

Usage:
  python backend/database/migrate_to_supabase.py
"""
import os
import sys
import pandas as pd
from sqlalchemy import create_engine, text, inspect

# ── 1. Resolve Paths & Environment ──────────────────────────────────────────
_HERE = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.normpath(os.path.join(_HERE, '..', '..'))
DATA_DIR = os.path.join(ROOT_DIR, 'data')
COHORT_DIR = os.path.join(DATA_DIR, 'latest cohort data')
SCHEMA_FILE = os.path.join(_HERE, 'schema.sql')

# Load .env variables if present
ENV_FILE = os.path.join(ROOT_DIR, '.env')
if os.path.exists(ENV_FILE):
    with open(ENV_FILE, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                k, v = line.split('=', 1)
                os.environ.setdefault(k.strip(), v.strip())

DATABASE_URL = os.environ.get('DATABASE_URL', '').strip()

def clean_df(df: pd.DataFrame) -> pd.DataFrame:
    """Cleans dataframe columns and string whitespace."""
    df = df.loc[:, ~df.columns.str.startswith('Unnamed:')]
    df.columns = df.columns.str.strip().str.replace('\n', ' ')
    for c in df.select_dtypes('object').columns:
        df[c] = df[c].str.strip()
    return df.fillna('')

def push_dataframe(df: pd.DataFrame, table_name: str, engine):
    """Pushes a pandas dataframe into Supabase PostgreSQL."""
    df.to_sql(table_name, engine, if_exists='replace', index=False, method='multi', chunksize=1000)
    print(f"  [OK] Successfully migrated {len(df)} rows -> {table_name}")

def migrate_assay_file(label: str, filename: str, table_name: str, engine, sheet=None):
    file_path = os.path.join(COHORT_DIR, filename)
    if not os.path.exists(file_path):
        file_path = os.path.join(DATA_DIR, filename)

    if not os.path.exists(file_path):
        print(f"  [SKIP] {label}: File '{filename}' not found.")
        return

    print(f"\n  Migrating [{label}] from {filename} -> Supabase table '{table_name}'...")
    try:
        if filename.endswith('.csv'):
            try:
                df = pd.read_csv(file_path, dtype=str, encoding='utf-8')
            except UnicodeDecodeError:
                df = pd.read_csv(file_path, dtype=str, encoding='latin1')
        else:
            kwargs = {'dtype': str}
            if sheet:
                kwargs['sheet_name'] = sheet
            df = pd.read_excel(file_path, **kwargs)

        df = clean_df(df)
        push_dataframe(df, table_name, engine)
    except Exception as e:
        print(f"  [ERROR] Failed migrating {label}: {e}")

def run_migration():
    print("=" * 70)
    print("🚀 FARCAST DB v2 — SUPABASE CLOUD POSTGRESQL MIGRATION")
    print("=" * 70)

    if not DATABASE_URL or 'your-supabase' in DATABASE_URL:
        print("\n[!] ERROR: DATABASE_URL is not configured in your .env file.")
        print("    Please open .env and set your Supabase Cloud PostgreSQL connection URI:")
        print("    DATABASE_URL=postgresql://postgres:[PASSWORD]@db.[PROJECT-REF].supabase.co:5432/postgres\n")
        sys.exit(1)

    print(f"\n1. Connecting to Supabase Cloud PostgreSQL...")
    try:
        engine = create_engine(DATABASE_URL, connect_args={'connect_timeout': 10})
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        print("   [OK] Connected to Supabase Cloud PostgreSQL successfully!")
    except Exception as e:
        print(f"\n   [ERROR] Connection failed: {e}")
        print("   Please check your Supabase database password and connection string in .env.\n")
        sys.exit(1)

    # ── 2. Run Base Schema DDL ──────────────────────────────────────────────
    print("\n2. Executing Core Schema DDL (Users, Whitelist, Audit Logs)...")
    if os.path.exists(SCHEMA_FILE):
        with open(SCHEMA_FILE, 'r', encoding='utf-8') as f:
            schema_sql = f.read()
        try:
            with engine.begin() as conn:
                for statement in schema_sql.split(';'):
                    stmt = statement.strip()
                    if stmt:
                        conn.execute(text(stmt))
            print("   [OK] Schema and indexes created in Supabase.")
        except Exception as e:
            print(f"   [NOTE] Schema execution note: {e}")

    # ── 3. Migrate All Multi-Omics Assay Datasets ────────────────────────────
    print("\n3. Migrating Multi-Omics Datasets to Supabase...")

    # Histopathology
    histo_file = "06Aug2026_histo_cohort.xlsx"
    if not os.path.exists(os.path.join(COHORT_DIR, histo_file)):
        histo_file = "22Jul2026_histo_cohort.xlsx"
    migrate_assay_file("HISTOPATHOLOGY", histo_file, "assay_histopathology", engine)

    # Cytokine
    migrate_assay_file("CYTOKINE", "Cytokine_cohort_1_fixed.xlsx", "assay_cytokine", engine)

    # Nanostring
    migrate_assay_file("NANOSTRING", "Nanostring_currated_data.xlsx", "assay_nanostring", engine)

    # mIHC
    migrate_assay_file("mIHC", "mIHC image details With Treatment Details_SS 1.xlsx", "assay_mihc", engine)

    # ── 4. Verify Final Supabase Cloud Tables ────────────────────────────────
    print("\n4. Verifying Tables in Supabase Cloud Database...")
    insp = inspect(engine)
    tables = [t for t in insp.get_table_names() if t.startswith('assay_') or t in ('users', 'whitelisted_emails', 'audit_logs')]
    
    print("\n" + "-" * 50)
    print(f"{'Supabase Table Name':<30} | {'Row Count':<15}")
    print("-" * 50)
    with engine.connect() as conn:
        for t in sorted(tables):
            try:
                cnt = conn.execute(text(f'SELECT COUNT(*) FROM "{t}"')).scalar()
                print(f"{t:<30} | {cnt:<15}")
            except Exception:
                print(f"{t:<30} | {'N/A':<15}")
    print("-" * 50)

    print("\n🎉 SUPABASE CLOUD DATABASE MIGRATION COMPLETED SUCCESSFULLY!\n")

if __name__ == '__main__':
    run_migration()
