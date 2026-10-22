"""
FarCast DB — Assay Masterfiles Synchronization Module
Ingests Cytokine Release & Histopathology master readouts into Supabase.
"""
import os
import re
import glob
import logging
import pandas as pd
from sqlalchemy import text, Engine
from typing import Tuple, List, Dict, Set

from config import (
    CYTOKINE_DIR, HISTOPATHOLOGY_DIR, HISTO_ARCHIVE_DIR,
    HISTO_PROCESSING_DIR, CHUNK_SIZE
)
from logger import SyncMetrics

HISTO_COL_MAP = {
    'Necrosis_score': 'Necrosis_Score',
    'necrosis_score': 'Necrosis_Score',
    'KI67': 'Ki67',
    'ki67': 'Ki67',
    'Cas-3_Tumor': 'Cas-3',
    'cas-3_tumor': 'Cas-3',
    'cas-3': 'Cas-3',
    'cas3': 'Cas-3',
    'Cas-3-Immune': 'Cas-3_Immune',
    'cas-3-immune': 'Cas-3_Immune',
    'cas-3_immune': 'Cas-3_Immune',
}

CYTO_COL_MAP = {
    'IP-10 (CXCL10)': 'IP-10_CXCL10',
    'IL-8 (CXCL8)': 'IL-8_CXCL8',
    'IFN gamma': 'IFN-gamma',
    'TNF alpha': 'TNF-alpha',
    'Granzyme B': 'Granzyme_B',
    'IL-1 beta': 'IL-1beta',
    'IL-1Beta': 'IL-1beta',
    'Fractalkine (CX3CL1)': 'Fractalkine_CX3CL1',
    'G-CSF (CSF3)': 'G-CSF_CSF3',
    'I-TAC (CXCL11)': 'I-TAC_CXCL11',
    'MCP-1 (CCL2)': 'MCP-1_CCL2',
    'MIG (CXCL9)': 'MIG_CXCL9',
    'MIP-1 alpha (CCL3)': 'MIP-1alpha_CCL3',
    'MDC (CCL22)': 'MDC_CCL22',
    'Eotaxin-2 (CCL24)': 'Eotaxin-2_CCL24',
    'SDF-1 alpha (CXCL12)': 'SDF-1alpha_CXCL12',
    'Eotaxin (CCL11)': 'Eotaxin_CCL11',
    'RANTES (CCL5)': 'RANTES_CCL5',
    'MIP-1 beta (CCL4)': 'MIP-1beta_CCL4',
    'GRO alpha (CXCL1)': 'GRO-alpha_CXCL1',
    'MCP-3 (CCL7)': 'MCP-3_CCL7',
    'MCP-4 (CCL13)': 'MCP-4_CCL13',
}


def standardize_arm(arm_val) -> str:
    """Normalize arm string to strict uppercase alphanumeric (e.g. RxA -> RXA, Arm-1 -> ARM1)."""
    if pd.isna(arm_val) or arm_val is None:
        return ""
    s = str(arm_val).strip()
    return re.sub(r'[\s\-_]+', '', s).upper()


def sync_cytokine_assays(engine: Engine, metrics: SyncMetrics, logger: logging.Logger) -> Tuple[int, int]:
    """Ingest Cytokine masterfiles from server directories."""
    logger.info("=" * 60)
    logger.info("STEP 2A: Synchronizing Cytokine Release Assays")
    logger.info("=" * 60)
    logger.info(f"Target Directory: {CYTOKINE_DIR}")

    if not os.path.exists(CYTOKINE_DIR):
        logger.warning(f"Cytokine directory not found: {CYTOKINE_DIR}")
        metrics.warnings.append(f"Cytokine dir not found: {CYTOKINE_DIR}")
        return 0, 0

    run_dirs = sorted([
        os.path.join(CYTOKINE_DIR, d) for d in os.listdir(CYTOKINE_DIR)
        if os.path.isdir(os.path.join(CYTOKINE_DIR, d))
    ])
    logger.info(f"Discovered {len(run_dirs)} run subdirectories in Cytokine repo.")

    all_dfs = []
    runs_processed = 0

    for rdir in run_dirs:
        rname = os.path.basename(rdir)
        files = os.listdir(rdir)

        master_files = [f for f in files if 'masterfileformat' in f.lower() and f.endswith('.xlsx') and not f.startswith('~$')]
        if not master_files:
            continue

        chosen = master_files[0]
        fpath = os.path.join(rdir, chosen)

        try:
            xl = pd.ExcelFile(fpath)
            sheet = 'Sheet1' if 'Sheet1' in xl.sheet_names else xl.sheet_names[0]
            df = xl.parse(sheet, dtype=str)
            df = df.loc[:, ~df.columns.astype(str).str.startswith('Unnamed:')]
            df.rename(columns=CYTO_COL_MAP, inplace=True)

            for c in df.columns:
                df[c] = df[c].fillna('').astype(str).str.strip().replace({'nan': '', 'None': '', 'NaN': ''})

            if 'Arms' in df.columns:
                df['Arms'] = df['Arms'].apply(standardize_arm)
            if 'Sample_ID' in df.columns:
                df['Sample_ID'] = df['Sample_ID'].str.strip()
                df = df[df['Sample_ID'].ne('') & df['Sample_ID'].ne('nan') & ~df['Sample_ID'].str.startswith('Unknown')]

            if not df.empty:
                all_dfs.append(df)
                runs_processed += 1
                logger.info(f"  Processed {rname} ({chosen}): {len(df)} rows across {df['Sample_ID'].nunique()} sample(s).")
        except Exception as e:
            logger.error(f"  Error reading {fpath}: {e}")
            metrics.warnings.append(f"Failed parsing cytokine run {rname}: {e}")

    if not all_dfs:
        logger.info("No valid cytokine rows extracted.")
        return 0, 0

    combined = pd.concat(all_dfs, ignore_index=True).fillna('')
    unique_sids = combined['Sample_ID'].unique().tolist()
    logger.info(f"Total extracted Cytokine rows: {len(combined)} across {len(unique_sids)} unique samples.")

    with engine.connect() as conn:
        db_cols = [
            r[0] for r in conn.execute(text(
                "SELECT column_name FROM information_schema.columns "
                "WHERE table_name='assay_cytokine' ORDER BY ordinal_position"
            )).fetchall()
        ]

    for c in db_cols:
        if c not in combined.columns:
            combined[c] = ''
    combined = combined[db_cols]

    inserted = 0
    with engine.connect() as conn:
        for start in range(0, len(combined), CHUNK_SIZE):
            chunk = combined.iloc[start:start + CHUNK_SIZE]
            chunk_sids = chunk['Sample_ID'].unique().tolist()
            with conn.begin():
                conn.execute(
                    text('DELETE FROM "assay_cytokine" WHERE "Sample_ID" = ANY(:sids)'),
                    {'sids': chunk_sids}
                )
                chunk.to_sql('assay_cytokine', conn, if_exists='append', index=False)
            inserted += len(chunk)

    metrics.cyto_runs_processed = runs_processed
    metrics.cyto_rows_inserted = inserted
    metrics.cyto_unique_samples = len(unique_sids)
    logger.info(f"Successfully synchronized {inserted} Cytokine rows into Supabase.")
    return inserted, len(unique_sids)


def sync_histopathology_assays(engine: Engine, metrics: SyncMetrics, logger: logging.Logger) -> Tuple[int, int]:
    """Ingest Histopathology master files from designated directories."""
    logger.info("=" * 60)
    logger.info("STEP 2B: Synchronizing Histopathology Assays")
    logger.info("=" * 60)

    search_dirs = [HISTOPATHOLOGY_DIR, HISTO_ARCHIVE_DIR, HISTO_PROCESSING_DIR]
    valid_dirs = [d for d in search_dirs if os.path.exists(d)]
    logger.info(f"Checking Histopathology directories: {valid_dirs}")

    discovered_files = []
    for base_dir in valid_dirs:
        for root, _, files in os.walk(base_dir):
            for f in files:
                if f.endswith('.xlsx') and not f.startswith('~$') and not f.startswith('._'):
                    discovered_files.append(os.path.join(root, f))

    logger.info(f"Discovered {len(discovered_files)} Histopathology Excel files across directories.")
    if not discovered_files:
        logger.info("No Histopathology files found to ingest.")
        return 0, 0

    all_dfs = []
    files_processed = 0

    for fpath in discovered_files:
        fname = os.path.basename(fpath)
        sample_guess = os.path.splitext(fname)[0].split('.')[0].split('_')[0].strip()

        try:
            xl = pd.ExcelFile(fpath)
            target_sheet = None
            for s in xl.sheet_names:
                if 'master' in s.lower():
                    target_sheet = s
                    break

            df = None
            if target_sheet:
                df = xl.parse(target_sheet, dtype=str)
            else:
                for s in xl.sheet_names:
                    try:
                        temp_df = xl.parse(s, nrows=5, dtype=str)
                        cols_lower = [str(c).strip().lower() for c in temp_df.columns]
                        if 'arms' in cols_lower or 'arm' in cols_lower:
                            df = xl.parse(s, dtype=str)
                            break
                    except Exception:
                        pass

            if df is None:
                continue

            df = df.loc[:, ~df.columns.astype(str).str.startswith('Unnamed:')]
            df.columns = [c.strip() for c in df.columns]
            for col in list(df.columns):
                if col.lower() in ('arms', 'arm', 'arm_code'):
                    df.rename(columns={col: 'Arms'}, inplace=True)
                elif col.lower() in ('sample_id', 'sample id', 'sampleid'):
                    df.rename(columns={col: 'Sample_ID'}, inplace=True)

            df.rename(columns=HISTO_COL_MAP, inplace=True)

            for c in df.columns:
                df[c] = df[c].fillna('').astype(str).str.strip().replace({'nan': '', 'None': '', 'NaN': ''})

            if 'Sample_ID' not in df.columns or df['Sample_ID'].eq('').all():
                df['Sample_ID'] = sample_guess
            else:
                df['Sample_ID'] = df['Sample_ID'].replace('', sample_guess)

            if 'Arms' in df.columns:
                df['Arms'] = df['Arms'].apply(standardize_arm)
            else:
                continue

            if 'Timepoint' in df.columns:
                df['Timepoint'] = df['Timepoint'].str.upper()
            if 'Plate_NO' in df.columns:
                df['Plate_NO'] = df['Plate_NO'].str.upper()

            df = df[df['Sample_ID'].ne('') & df['Arms'].ne('')]
            if not df.empty:
                all_dfs.append(df)
                files_processed += 1
                logger.info(f"  Processed {fname}: {len(df)} rows, arms: {df['Arms'].unique().tolist()}")
        except Exception as e:
            logger.error(f"  Error reading {fname}: {e}")
            metrics.warnings.append(f"Failed parsing histo file {fname}: {e}")

    if not all_dfs:
        logger.info("No valid Histopathology rows parsed.")
        return 0, 0

    combined = pd.concat(all_dfs, ignore_index=True).fillna('')
    unique_sids = combined['Sample_ID'].unique().tolist()
    logger.info(f"Total extracted Histopathology rows: {len(combined)} across {len(unique_sids)} unique samples.")

    with engine.connect() as conn:
        db_cols = [
            r[0] for r in conn.execute(text(
                "SELECT column_name FROM information_schema.columns "
                "WHERE table_name='assay_histopathology' ORDER BY ordinal_position"
            )).fetchall()
        ]

    for c in db_cols:
        if c not in combined.columns:
            combined[c] = ''
    combined = combined[db_cols]

    inserted = 0
    with engine.connect() as conn:
        for start in range(0, len(combined), CHUNK_SIZE):
            chunk = combined.iloc[start:start + CHUNK_SIZE]
            chunk_sids = chunk['Sample_ID'].unique().tolist()
            with conn.begin():
                conn.execute(
                    text('DELETE FROM "assay_histopathology" WHERE "Sample_ID" = ANY(:sids)'),
                    {'sids': chunk_sids}
                )
                chunk.to_sql('assay_histopathology', conn, if_exists='append', index=False)
            inserted += len(chunk)

    metrics.histo_files_processed = files_processed
    metrics.histo_rows_inserted = inserted
    metrics.histo_unique_samples = len(unique_sids)
    logger.info(f"Successfully synchronized {inserted} Histopathology rows into Supabase.")
    return inserted, len(unique_sids)
