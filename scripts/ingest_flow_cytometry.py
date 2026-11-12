#!/usr/bin/env python3
"""
FarCast DB v2 — Flow Cytometry Data Ingestion Script
===================================================
Creates the "assay_flow_cytometry" table in Supabase Cloud PostgreSQL (if not exists)
and ingests curated Flow Cytometry data from Flow_curated_data.xlsx.

Usage:
------
python scripts/ingest_flow_cytometry.py
python scripts/ingest_flow_cytometry.py --file "C:\\path\\to\\Flow_curated_data.xlsx"
python scripts/ingest_flow_cytometry.py --dry-run
"""

import os
import sys
import argparse
import requests
import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
ENV_PATH = os.path.join(BASE_DIR, ".env")
load_dotenv(ENV_PATH)

DEFAULT_FILE = os.path.join(BASE_DIR, "Flow_curated_data.xlsx")


def get_db_engine():
    """Establish connection to Supabase Cloud PostgreSQL."""
    db_url = os.environ.get("DATABASE_URL", "").strip()
    if not db_url:
        raise ValueError(f"DATABASE_URL not found in environment or {ENV_PATH}")

    if db_url.startswith('postgres://'):
        db_url = db_url.replace('postgres://', 'postgresql+psycopg2://', 1)
    elif db_url.startswith('postgresql://'):
        db_url = db_url.replace('postgresql://', 'postgresql+psycopg2://', 1)

    return create_engine(db_url, connect_args={'connect_timeout': 15})


def parse_flow_file(fpath: str) -> pd.DataFrame:
    """Parse Flow Cytometry Excel file and return cleaned DataFrame."""
    if not os.path.exists(fpath):
        raise FileNotFoundError(f"File not found: {fpath}")

    xl = pd.ExcelFile(fpath)
    sheet_name = None
    for s in xl.sheet_names:
        if 'flow' in s.lower() and 'curated' in s.lower():
            sheet_name = s
            break
        if 'flow' in s.lower():
            sheet_name = s

    if not sheet_name:
        sheet_name = xl.sheet_names[0]

    df = xl.parse(sheet_name, dtype=str)
    # Drop Unnamed columns
    df = df.loc[:, ~df.columns.astype(str).str.startswith('Unnamed:')]
    df.columns = [str(c).strip() for c in df.columns]

    # Clean string columns
    for c in df.columns:
        df[c] = df[c].fillna('').astype(str).str.strip()

    # Reorder columns standardly: Sample_ID first, then metadata / path fields
    pref = ["Sample_ID", "Name", "Study", "Arm", "Location", "Full_Path"]
    ordered = [c for c in pref if c in df.columns]
    remaining = [c for c in df.columns if c not in ordered]
    df = df[ordered + remaining]

    # Filter out empty Sample_IDs
    df = df[df["Sample_ID"].ne("")]
    return df.reset_index(drop=True)


def ingest_flow_cytometry(fpath: str, dry_run: bool = False, trigger_refresh: bool = True):
    print("=" * 70)
    print("FarCast DB v2 — Flow Cytometry Supabase Ingestion")
    print("=" * 70)
    print(f"Target File : {fpath}")

    df = parse_flow_file(fpath)
    unique_sids = sorted(df['Sample_ID'].unique().tolist())

    print(f"Parsed Rows : {len(df):,}")
    print(f"Unique Sample IDs ({len(unique_sids):02d}) : {', '.join(unique_sids[:15])}...")
    print(f"Columns ({len(df.columns)}) : {', '.join(df.columns)}")

    if dry_run:
        print("\n[DRY RUN MODE] No changes made to Supabase.")
        return

    print("\nConnecting to Supabase Cloud PostgreSQL...")
    engine = get_db_engine()

    # 1. Create table & indexes if not exists
    table_name = "assay_flow_cytometry"
    create_sql = f"""
    CREATE TABLE IF NOT EXISTS "{table_name}" (
        "Sample_ID" TEXT,
        "Name" TEXT,
        "Study" TEXT,
        "Arm" TEXT,
        "Location" TEXT,
        "Full_Path" TEXT
    );
    CREATE INDEX IF NOT EXISTS "idx_{table_name}_sample_id" ON "{table_name}" ("Sample_ID");
    CREATE INDEX IF NOT EXISTS "idx_{table_name}_arm" ON "{table_name}" ("Arm");
    CREATE INDEX IF NOT EXISTS "idx_{table_name}_study" ON "{table_name}" ("Study");
    """

    with engine.begin() as conn:
        conn.execute(text(create_sql))

    # 2. Check current row count
    with engine.connect() as conn:
        before_count = conn.execute(text(f'SELECT count(*) FROM "{table_name}"')).scalar()

    print(f"Current records in '{table_name}': {before_count:,}")

    # 3. Replace/upsert records
    print(f"Deleting pre-existing records for {len(unique_sids)} incoming samples...")
    with engine.begin() as conn:
        conn.execute(
            text(f'DELETE FROM "{table_name}" WHERE "Sample_ID" = ANY(:sids)'),
            {'sids': unique_sids}
        )

    # 4. Insert in chunks
    chunk_size = 500
    inserted = 0
    print(f"Ingesting {len(df):,} rows into Supabase in chunks of {chunk_size}...")
    with engine.connect() as conn:
        for start in range(0, len(df), chunk_size):
            chunk = df.iloc[start:start + chunk_size]
            with conn.begin():
                chunk.to_sql(table_name, conn, if_exists='append', index=False)
            inserted += len(chunk)
            print(f"  Committed rows {inserted:,} / {len(df):,}...")

    with engine.connect() as conn:
        after_count = conn.execute(text(f'SELECT count(*) FROM "{table_name}"')).scalar()

    print("\n" + "=" * 70)
    print("SUCCESS: Flow Cytometry Ingestion Completed!")
    print(f"  Rows Inserted / Updated : {inserted:,}")
    print(f"  Previous Total Rows     : {before_count:,}")
    print(f"  New Total Rows in DB    : {after_count:,}")
    print("=" * 70)

    # 5. Reload Application In-Memory Cache
    if trigger_refresh:
        print("\nTriggering live application cache refresh...")
        refresh_urls = [
            os.environ.get("LOCAL_REFRESH_URL", "http://localhost:5052/api/refresh").strip(),
            os.environ.get("RAILWAY_APP_URL", "").strip().rstrip("/") + "/api/refresh" if os.environ.get("RAILWAY_APP_URL") else None
        ]
        for url in filter(None, refresh_urls):
            try:
                resp = requests.get(url, timeout=10)
                if resp.status_code == 200:
                    data = resp.json()
                    flow_cnt = data.get("assays", {}).get("Flow Cytometry", "N/A")
                    print(f"  [OK] Cache reloaded successfully on: {url} (Loaded Flow Cytometry rows: {flow_cnt})")
                else:
                    print(f"  [NOTE] Cache reload responded with status {resp.status_code} on: {url}")
            except Exception:
                print(f"  [NOTE] Server at {url} not currently active (in-memory cache will refresh on next start).")


def main():
    parser = argparse.ArgumentParser(description="Ingest Flow Cytometry Excel data into Supabase Cloud")
    parser.add_argument(
        "--file",
        type=str,
        default=DEFAULT_FILE,
        help="Path to Flow_curated_data.xlsx"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate and preview without making changes in Supabase"
    )
    parser.add_argument(
        "--no-refresh",
        action="store_true",
        help="Skip triggering /api/refresh"
    )

    args = parser.parse_args()
    ingest_flow_cytometry(
        fpath=args.file,
        dry_run=args.dry_run,
        trigger_refresh=not args.no_refresh
    )


if __name__ == "__main__":
    main()

