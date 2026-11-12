#!/usr/bin/env python3
"""
FarCast DB v2 — Dedicated Histopathology Data Ingestion Script
=============================================================
Ingests curated Histopathology master data Excel files into Supabase Cloud PostgreSQL ("assay_histopathology").

Usage:
------
1. Ingest default curated directory:
   python scripts/ingest_histopathology.py

2. Ingest a specific directory:
   python scripts/ingest_histopathology.py --dir "C:\\path\\to\\curated_samples"

3. Ingest a single file:
   python scripts/ingest_histopathology.py --file "C:\\path\\to\\sample_file.xlsx"

4. Dry run (validate files and preview without inserting into Supabase):
   python scripts/ingest_histopathology.py --dry-run
"""

import os
import sys
import glob
import re
import argparse
import requests
import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

# Base directories
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
ENV_PATH = os.path.join(BASE_DIR, ".env")
load_dotenv(ENV_PATH)

# Standardize Column Aliases
HISTO_COL_MAP = {
    'necrosis_score': 'Necrosis_Score',
    'necrosis score': 'Necrosis_Score',
    'ki67': 'Ki67',
    'ki-67': 'Ki67',
    'cas-3_tumor': 'Cas-3',
    'cas-3': 'Cas-3',
    'cas3': 'Cas-3',
    'cas-3-immune': 'Cas-3_Immune',
    'cas-3_immune': 'Cas-3_Immune',
    'tumoral_cd8_count': 'Intratumoral_CD8',
    'tumoral_cd8': 'Intratumoral_CD8',
    'intratumoral_cd8_count': 'Intratumoral_CD8',
    'intratumoral_cd8': 'Intratumoral_CD8',
    'stromal_cd8_count': 'Stromal_CD8',
    'stromal_cd8': 'Stromal_CD8',
}


def clean_scalar(val) -> str:
    """Format and clean individual values for PostgreSQL text columns."""
    if pd.isna(val) or val is None:
        return ''
    if isinstance(val, (float, int)):
        if isinstance(val, float) and val.is_integer():
            return str(int(val))
        return str(val)
    s = str(val).strip()
    if s.lower() in ('nan', 'none', 'null'):
        return ''
    if re.match(r'^-?\d+\.0$', s):
        return s.split('.')[0]
    return s


def standardize_arm(arm_val) -> str:
    """Normalize arm string to strict uppercase alphanumeric (e.g. Rx-A -> RXA, Arm-1 -> ARM1)."""
    if pd.isna(arm_val) or arm_val is None:
        return ""
    s = str(arm_val).strip()
    return re.sub(r'[\s\-_]+', '', s).upper()


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


def parse_excel_file(fpath: str) -> pd.DataFrame:
    """Parse a single Histopathology Excel file and return cleaned DataFrame."""
    fname = os.path.basename(fpath)
    # Extract sample ID guess from filename (e.g. FBB1B210071.xlsx_Histopathology... -> FBB1B210071)
    sample_guess = fname.split('.')[0].split('_')[0].strip()

    xl = pd.ExcelFile(fpath)
    sheet_names = xl.sheet_names

    # Priority 1: 'Master' sheet
    target_sheet = None
    for s in sheet_names:
        if 'master' in s.lower():
            target_sheet = s
            break

    df = None
    if target_sheet:
        df = xl.parse(target_sheet, dtype=object)
    else:
        # Priority 2: sheet containing 'Arms' or 'Arm' column
        for s in sheet_names:
            try:
                temp_df = xl.parse(s, nrows=5, dtype=object)
                cols_lower = [str(c).strip().lower() for c in temp_df.columns]
                if 'arms' in cols_lower or 'arm' in cols_lower:
                    df = xl.parse(s, dtype=object)
                    target_sheet = s
                    break
            except Exception:
                pass

    if df is None:
        raise ValueError(f"No 'Master' sheet or sheet with 'Arms' column found in {sheet_names}")

    # Drop Unnamed columns
    df = df.loc[:, ~df.columns.astype(str).str.startswith('Unnamed:')]
    df.columns = [str(c).strip() for c in df.columns]

    # Standardize column names
    col_rename = {}
    for c in df.columns:
        clow = c.lower()
        if clow in ('arms', 'arm', 'arm_code'):
            col_rename[c] = 'Arms'
        elif clow in ('sample_id', 'sample id', 'sampleid'):
            col_rename[c] = 'Sample_ID'
        elif clow in HISTO_COL_MAP:
            col_rename[c] = HISTO_COL_MAP[clow]

    df.rename(columns=col_rename, inplace=True)

    # Ensure Sample_ID column
    if 'Sample_ID' not in df.columns:
        df['Sample_ID'] = sample_guess
    else:
        df['Sample_ID'] = df['Sample_ID'].fillna(sample_guess).replace('', sample_guess)
        df['Sample_ID'] = df['Sample_ID'].astype(str).str.strip()

    # Standardize Arms
    if 'Arms' not in df.columns:
        raise ValueError("Missing 'Arms' column after parsing")

    df['Arms'] = df['Arms'].apply(standardize_arm)
    df = df[df['Arms'].ne('') & df['Sample_ID'].ne('')]

    # Standardize Plate_NO & Timepoint
    if 'Plate_NO' in df.columns:
        df['Plate_NO'] = df['Plate_NO'].astype(str).str.strip().str.upper()
    if 'Timepoint' in df.columns:
        df['Timepoint'] = df['Timepoint'].astype(str).str.strip().str.upper()

    # Clean all cell values
    for col in df.columns:
        df[col] = df[col].apply(clean_scalar)

    return df


def ingest_histopathology(target_path: str, dry_run: bool = False, trigger_refresh: bool = True):
    print("=" * 70)
    print("FarCast DB v2 — Histopathology Supabase Ingestion")
    print("=" * 70)

    # 1. Discover files
    if os.path.isfile(target_path):
        excel_files = [target_path]
    elif os.path.isdir(target_path):
        all_found = glob.glob(os.path.join(target_path, "**", "*.xlsx"), recursive=True)
        excel_files = [
            f for f in all_found
            if not os.path.basename(f).startswith("~$") and not os.path.basename(f).startswith("._")
        ]
    else:
        print(f"[ERROR] Path not found: {target_path}")
        sys.exit(1)

    print(f"Target Path     : {target_path}")
    print(f"Excel Files Found: {len(excel_files)}")
    if not excel_files:
        print("[WARNING] No valid .xlsx files found to ingest.")
        return

    # 2. Parse all files
    parsed_dfs = []
    errors = []
    print("\nParsing Excel files...")
    for idx, fpath in enumerate(excel_files, 1):
        fname = os.path.basename(fpath)
        try:
            df = parse_excel_file(fpath)
            if not df.empty:
                parsed_dfs.append(df)
                sids = df['Sample_ID'].unique().tolist()
                print(f"  [{idx:02d}/{len(excel_files):02d}] {fname} -> {len(df)} rows (Sample: {', '.join(sids)})")
            else:
                print(f"  [{idx:02d}/{len(excel_files):02d}] {fname} -> 0 valid rows (Skipped)")
        except Exception as e:
            errors.append((fname, str(e)))
            print(f"  [{idx:02d}/{len(excel_files):02d}] {fname} -> [ERROR] {e}")

    if not parsed_dfs:
        print("\n[ERROR] No valid data could be parsed from the files.")
        return

    combined_df = pd.concat(parsed_dfs, ignore_index=True)
    unique_sids = sorted(combined_df['Sample_ID'].unique().tolist())
    print("\n" + "-" * 70)
    print(f"Extraction Summary:")
    print(f"  Files Successfully Processed : {len(parsed_dfs)} / {len(excel_files)}")
    print(f"  Total Extracted Rows         : {len(combined_df):,}")
    print(f"  Unique Sample IDs ({len(unique_sids):02d})     : {', '.join(unique_sids)}")
    if errors:
        print(f"  Errors Encountered           : {len(errors)}")

    if dry_run:
        print("\n[DRY RUN MODE] No changes made to Supabase.")
        return

    # 3. Connect to Supabase and align schema
    print("\nConnecting to Supabase Cloud PostgreSQL...")
    engine = get_db_engine()

    with engine.connect() as conn:
        before_count = conn.execute(text('SELECT count(*) FROM "assay_histopathology"')).scalar()
        db_cols = [
            r[0] for r in conn.execute(text(
                "SELECT column_name FROM information_schema.columns "
                "WHERE table_name='assay_histopathology' ORDER BY ordinal_position"
            )).fetchall()
        ]

    print(f"  Current row count in 'assay_histopathology': {before_count:,}")
    print(f"  Database Columns ({len(db_cols)}): {', '.join(db_cols[:8])}...")

    # Ensure any new columns in incoming data exist in Supabase table
    new_cols = [c for c in combined_df.columns if c not in db_cols]
    if new_cols:
        print(f"  Adding {len(new_cols)} new column(s) to 'assay_histopathology': {', '.join(new_cols)}")
        with engine.begin() as conn:
            for nc in new_cols:
                conn.execute(text(f'ALTER TABLE "assay_histopathology" ADD COLUMN IF NOT EXISTS "{nc}" TEXT'))
        with engine.connect() as conn:
            db_cols = [
                r[0] for r in conn.execute(text(
                    "SELECT column_name FROM information_schema.columns "
                    "WHERE table_name='assay_histopathology' ORDER BY ordinal_position"
                )).fetchall()
            ]

    # Align columns strictly to Supabase table
    for c in db_cols:
        if c not in combined_df.columns:
            combined_df[c] = ''
    aligned_df = combined_df[db_cols]

    # 4. Upsert into Supabase (delete existing records for all unique incoming Sample_IDs, then append fresh rows)
    chunk_size = 500
    inserted_count = 0

    print(f"\nDeleting any pre-existing records for {len(unique_sids)} incoming samples...")
    with engine.begin() as conn:
        conn.execute(
            text('DELETE FROM "assay_histopathology" WHERE "Sample_ID" = ANY(:sids)'),
            {'sids': unique_sids}
        )

    print(f"Ingesting {len(aligned_df):,} rows into Supabase in chunks of {chunk_size}...")
    with engine.connect() as conn:
        for start in range(0, len(aligned_df), chunk_size):
            chunk = aligned_df.iloc[start:start + chunk_size]
            with conn.begin():
                chunk.to_sql('assay_histopathology', conn, if_exists='append', index=False)
            inserted_count += len(chunk)
            print(f"  Committed rows {inserted_count:,} / {len(aligned_df):,}...")

    with engine.connect() as conn:
        after_count = conn.execute(text('SELECT count(*) FROM "assay_histopathology"')).scalar()

    print("\n" + "=" * 70)
    print("SUCCESS: Ingestion Completed!")
    print(f"  Rows Inserted / Updated : {inserted_count:,}")
    print(f"  Previous Total Rows     : {before_count:,}")
    print(f"  New Total Rows in DB    : {after_count:,} (+{after_count - before_count:,})")
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
                    histo_cnt = data.get("assays", {}).get("Histopathology", "N/A")
                    print(f"  [OK] Cache reloaded successfully on: {url} (Loaded Histopathology rows: {histo_cnt})")
                else:
                    print(f"  [NOTE] Cache reload responded with status {resp.status_code} on: {url}")
            except Exception:
                print(f"  [NOTE] Server at {url} not currently active (in-memory cache will refresh on next start).")


def main():
    parser = argparse.ArgumentParser(description="Ingest Histopathology Excel data into Supabase Cloud")
    parser.add_argument(
        "--dir",
        type=str,
        default=os.path.join(BASE_DIR, "BP_shravan_curated_samples"),
        help="Directory containing curated Histopathology .xlsx files"
    )
    parser.add_argument(
        "--file",
        type=str,
        default=None,
        help="Path to a single Histopathology .xlsx file"
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
    target_path = args.file if args.file else args.dir
    ingest_histopathology(
        target_path=target_path,
        dry_run=args.dry_run,
        trigger_refresh=not args.no_refresh
    )


if __name__ == "__main__":
    main()
