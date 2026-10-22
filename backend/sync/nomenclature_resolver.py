"""
FarCast DB v2 — Treatment Details & Nomenclature Resolver Module
Resolves Arm Codes against the Indication-specific Nomenclature Template to produce 'overlay' records.
"""
import os
import re
import logging
import pandas as pd
from sqlalchemy import text, Engine
from typing import Dict, Tuple, Set

from .config import NOMENCLATURE_EXCEL_PATH, CHUNK_SIZE
from .logger import SyncMetrics

INDICATION_SHEET_MAP = {
    'hnscc': 'HNSCC',
    'head and neck': 'HNSCC',
    'head & neck': 'HNSCC',
    'cabr': 'CaBr',
    'ca breast': 'CaBr',
    'breast': 'CaBr',
    'ovary': 'Ovary',
    'ca ovary': 'Ovary',
    'ovarian': 'Ovary',
    'rcc': 'RCC',
    'kidney': 'RCC',
    'renal': 'RCC',
    'prostate': 'Prostrate',
    'prostrate': 'Prostrate',
    'lung': 'Lung',
    'nsclc': 'Lung',
    'crc': 'CRC',
    'colorectal': 'CRC',
    'colon': 'CRC',
    'rectal': 'CRC',
    'gastric': 'Gastric',
    'stomach': 'Gastric',
    'gi': 'Gastric',
    'pbmc': 'PBMC',
    'blood': 'PBMC',
    'healthy blood': 'PBMC',
    'esophagus': 'Esophagus',
    'esophageal': 'Esophagus',
}


def standardize_arm(arm_val) -> str:
    if pd.isna(arm_val) or arm_val is None:
        return ""
    s = str(arm_val).strip()
    return re.sub(r'[\s\-_]+', '', s).upper()


def build_nomenclature_lookup(excel_path: str, logger: logging.Logger) -> Tuple[Dict[Tuple[str, str], str], Dict[str, str]]:
    """
    Parse Nomenclature workbook across all Indication tabs.
    Returns:
      - specific_lookup: {(sheet_name_upper, arm_code_upper): drug_name}
      - global_fallback: {arm_code_upper: drug_name}
    """
    if not os.path.exists(excel_path):
        raise FileNotFoundError(f"Nomenclature Excel not found at: {excel_path}")

    xl = pd.ExcelFile(excel_path)
    specific_lookup = {}
    global_fallback = {}

    drug_cols = ['Drug1', 'Drug2', 'Drug3', 'Drug4', 'Drug5']

    for sheet in xl.sheet_names:
        if sheet.lower() in ('dropdown details', 'sheet1'):
            continue

        sheet_key = sheet.strip().upper()
        df = xl.parse(sheet, dtype=str)
        if 'Arm Nomenclature' not in df.columns:
            continue

        for _, row in df.iterrows():
            raw_arm = row.get('Arm Nomenclature')
            norm_arm = standardize_arm(raw_arm)
            if not norm_arm:
                continue

            # Build combined drug string
            drugs = []
            for col in drug_cols:
                if col in row and pd.notna(row[col]):
                    d_val = str(row[col]).strip()
                    if d_val and d_val.lower() not in ('nan', 'none', 'null', '0', '0.0'):
                        drugs.append(d_val)

            if drugs:
                drug_str = " + ".join(drugs)
            elif norm_arm in ('RXA', 'ARM1', 'T0'):
                drug_str = 'Control'
            else:
                drug_str = ''

            if drug_str:
                specific_lookup[(sheet_key, norm_arm)] = drug_str
                if norm_arm not in global_fallback:
                    global_fallback[norm_arm] = drug_str

    logger.info(f"Loaded {len(specific_lookup)} specific indication arm mappings and {len(global_fallback)} fallback arms.")
    return specific_lookup, global_fallback


def resolve_sample_indication(cancer_type: str) -> str:
    """Map sample CancerType string from metadata to Nomenclature sheet name."""
    if not cancer_type:
        return 'OTHER INDICATION'
    clean = str(cancer_type).strip().lower()
    for prefix, sheet_name in INDICATION_SHEET_MAP.items():
        if prefix in clean:
            return sheet_name.upper()
    return 'OTHER INDICATION'


def extract_year(val) -> str:
    if not val or pd.isna(val):
        return ''
    s = str(val).strip()
    if not s or s.lower() in ('nan', 'none', 'null'):
        return ''
    if len(s) >= 4 and s[:4].isdigit() and 2010 <= int(s[:4]) <= 2035:
        return s[:4]
    if len(s) >= 4 and s[-4:].isdigit() and 2010 <= int(s[-4:]) <= 2035:
        return s[-4:]
    m = re.search(r'(20\d\d)', s)
    if m:
        return m.group(1)
    return ''


def clean_drug_value(d, arm_code='') -> str:
    if not d or pd.isna(d):
        return ''
    d_clean = str(d).strip()
    if d_clean.lower() == 'control':
        return 'Control'
    d_upper = d_clean.upper()
    if any(phrase in d_upper for phrase in [
        'NOT MENTIONED', 'MISSED DETAILS', 'INSERT STUDY', 'TX RECEIVED WITH', 'DRUG DETAILS'
    ]):
        return ''
    if d_upper.startswith('ARM') or d_upper.startswith('RX'):
        return ''
    return d_clean


def arm_to_rx(arm_code: str) -> str:
    if arm_code.startswith('ARM') and arm_code[3:].isdigit():
        num = int(arm_code[3:])
        if 1 <= num <= 26:
            return 'RX' + chr(ord('A') + num - 1)
    return arm_code


def sync_treatment_overlay(engine: Engine, metrics: SyncMetrics, logger: logging.Logger) -> Tuple[int, int]:
    """
    Generate and upsert treatment overlay mappings in Supabase strictly using
    the official Nomenclature Template (Nomenclature_protected_Mar2025.xlsx).
    - No historical tracking sources or artificial baseline overlays.
    - Samples without assay evidence are NOT given artificial RXA rows.
    """
    logger.info("=" * 60)
    logger.info("STEP 3: Resolving Treatment Details & Arm Nomenclature (Office Template)")
    logger.info("=" * 60)

    # 1. Build Nomenclature Lookups from official Nomenclature Excel
    specific_lookup, global_fallback = build_nomenclature_lookup(NOMENCLATURE_EXCEL_PATH, logger)

    with engine.connect() as conn:
        # 2. Fetch Sample IDs and Indications from metadata
        meta_rows = conn.execute(text('SELECT "Sample_ID", "CancerType" FROM "metadata"')).fetchall()
        sample_ind_map = {r[0].strip(): resolve_sample_indication(r[1]) for r in meta_rows if r[0]}
        logger.info(f"Retrieved {len(sample_ind_map)} sample indications from metadata.")

        # 3. Fetch all active arms across Histopathology and Cytokines (STRICT EVIDENCE ONLY)
        histo_arms = conn.execute(text('SELECT DISTINCT "Sample_ID", "Arms" FROM "assay_histopathology"')).fetchall()
        cyto_arms = conn.execute(text('SELECT DISTINCT "Sample_ID", "Arms" FROM "assay_cytokine"')).fetchall()

    sample_arms_map: Dict[str, Set[str]] = {}
    for sid, arm in histo_arms + cyto_arms:
        if not sid or not arm:
            continue
        sid_clean = sid.strip()
        arm_clean = standardize_arm(arm)
        if arm_clean:
            sample_arms_map.setdefault(sid_clean, set()).add(arm_clean)

    logger.info(f"Discovered actual assay arms for {len(sample_arms_map)} samples across assays.")

    # 4. Resolve Drug for each (Sample_ID, Arm) strictly using official Nomenclature
    overlay_records = []
    unmatched_arms = set()

    for sid, arms in sample_arms_map.items():
        ind_sheet = sample_ind_map.get(sid, 'OTHER INDICATION')

        for arm in sorted(arms):
            rx_arm = arm_to_rx(arm)
            drug = specific_lookup.get((ind_sheet, arm)) or specific_lookup.get((ind_sheet, rx_arm))
            if not drug:
                drug = global_fallback.get(arm) or global_fallback.get(rx_arm)
            if not drug:
                if arm in ('RXA', 'ARM1', 'T0'):
                    drug = 'Control'
                else:
                    drug = ''
                    unmatched_arms.add(f"{ind_sheet}::{arm}")

            if drug:
                drug = clean_drug_value(drug)
                overlay_records.append({
                    'Sample_ID': sid,
                    'Arm_Code': arm,
                    'Drug': drug
                })

    metrics.overlay_unmatched_arms = sorted(list(unmatched_arms))
    if unmatched_arms:
        logger.warning(f"Unmatched arm codes found ({len(unmatched_arms)}): {list(unmatched_arms)[:10]}")

    df_overlay = pd.DataFrame(overlay_records).drop_duplicates(subset=['Sample_ID', 'Arm_Code'])
    logger.info(f"Generated {len(df_overlay)} distinct overlay mappings for {df_overlay['Sample_ID'].nunique()} samples.")
    logger.info(f"Unique drugs: {df_overlay['Drug'].nunique()}")

    # 5. Atomic Upsert into Supabase overlay table
    with engine.connect() as conn:
        with conn.begin():
            conn.execute(text('DROP TABLE IF EXISTS "overlay" CASCADE;'))
            df_overlay.to_sql('overlay', conn, if_exists='replace', index=False)
            conn.execute(text('CREATE INDEX IF NOT EXISTS idx_overlay_sid ON "overlay"("Sample_ID");'))
            conn.execute(text('CREATE INDEX IF NOT EXISTS idx_overlay_arm ON "overlay"("Arm_Code");'))

    metrics.overlay_total_rows = len(df_overlay)
    metrics.overlay_samples_covered = df_overlay['Sample_ID'].nunique()
    logger.info(f"Successfully synchronized {len(df_overlay)} rows into Supabase 'overlay' table.")
    return len(df_overlay), df_overlay['Sample_ID'].nunique()
