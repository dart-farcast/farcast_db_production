"""
FarCast DB — Robust Metadata Synchronization Module
Reads the office server registration workbook and upserts clinical metadata into Supabase.
"""
import os
import shutil
import tempfile
import logging
import pandas as pd
from sqlalchemy import text, Engine
from typing import Tuple

from config import METADATA_EXCEL_PATH, CHUNK_SIZE
from logger import SyncMetrics

COL_MAP = {
    'Register': 'Sample_ID',
    'CASE No': 'CaseNo',
    'Register Type': 'RegisterType',
    'Primary study': 'Study',
    'PrimaryStudy': 'Study',
    'Sample Collection Date\n(dd-mm-yyyy)': 'CollectionDate',
    'Sample Collection Time (Tumor Excision)': 'Sample Collection Time (Tumor Excision)',
    'Month': 'Month',
    'Sample Received Date': 'Sample Received Date',
    'Sample ReachedTime': 'Sample ReachedTime',
    'Sample Received TAT': 'Sample Received TAT',
    'Ischemic time\n(in mins)': 'Ischemic time (in mins)',
    'Protocol': 'Protocol',
    'Patient ID': 'PatientID',
    'ICF': 'ICF',
    'Project': 'Project_ID',
    'Hospital': 'Hospital',
    'Physican': 'Physician',
    'Physician': 'Physician',
    'Cancer Type': 'CancerType',
    'Cancer Sub Type': 'CancerSubType',
    'Tumor Site': 'TumorSite',
    'Tumor Site Details': 'TumorSiteDetails',
    'Gender': 'Gender',
    'Age': 'Age',
    'Infection Status': 'InfectionStatus',
    'Temp': 'Temperature',
    'Temperature': 'Temperature',
    'Logistic': 'Logistic',
    'Procedure Type': 'ProcedureType',
    'Sample Type': 'SampleType',
    'Therapy': 'Therapy',
    'cTNM': 'cTNM',
    'Cancer Stage-1': 'CancerStage',
    'Cancer Grade': 'CancerGrade',
    'pTNM': 'pTNM',
    'Treatment Cycles': 'TreatmentCycles',
    'Drug Name': 'DrugName',
    'Histopath': 'Histopath',
    'Post Surgery\nTreatment Arms': 'Post Surgery Treatment Arms',
    'Post Surgery\nDrug Name': 'Post Surgery Drug Name',
    'Sample Processing Date': 'ProcessingDate',
    'Sample Processing Start Time': 'Sample Processing Start Time',
    'Sample Processing End Time (in to culture)': 'Sample Processing End Time (in to culture)',
    'Total Processing Time': 'Total Processing Time',
    'Ext TAT': 'Ext TAT',
    'Actual TAT': 'Actual TAT',
    'Tissue Size pre processing\n(in cm)': 'Tissue Size pre processing (in cm)',
    'Tissue size post processing': 'TissueSizePostProcessing',
    'Explant Size': 'ExplantSize',
    'Room #': 'RoomNumber',
    'Processed By': 'ProcessedBy',
    'Blood qualified\n(Y/N)': 'Blood qualified (Y/N)',
    'Autologus Plasma Addition\n(Y/N)': 'Autologus Plasma Addition (Y/N)',
    'Co-culture': 'CoCulture',
    'Q1 Qualification for Tissue': 'Q1 Qualification for Tissue',
    'Q1 Qualification for Blood': 'Q1 Qualification for Blood',
    'Q1.5 Qualification (Compromised samples)': 'Q1.5 Qualification (Compromised samples)',
    'Q2 Qualification': 'Q2Qualification',
    'Reason for Q2': 'ReasonForQ2',
    'T0 - M/V T0(Arm x Replicates)': 'T0_MV',
    'Culture - M/V Tx (Arm x Replicates)': 'Culture_MVTx',
    'Total # of explants': 'TotalExplants',
    'Q2.5 Qualifiction': 'Q2_5_Qualification',
    'Q3 Qualification based on Pathology (>10% tumor content of 5 out of 7 at T0 and all arms of T72) (By Ritu)': 'Q3_Qualification',
    'Q4 Qualification': 'Q4_Qualification',
    'Final Qualification': 'FinalQualification',
    'Remarks': 'Remarks',
}


def read_excel_resilient(filepath: str, sheet_name: str, logger: logging.Logger) -> pd.DataFrame:
    """Read Excel file, falling back to a temp local copy if file is open/locked by another user."""
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"Metadata file not found on server at: {filepath}")

    try:
        return pd.read_excel(filepath, sheet_name=sheet_name, dtype=str)
    except (PermissionError, IOError) as lock_err:
        logger.warning(f"File lock or permission notice on {os.path.basename(filepath)}: {lock_err}. Attempting local copy read...")
        with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as tmp:
            tmp_path = tmp.name

        try:
            shutil.copyfile(filepath, tmp_path)
            df = pd.read_excel(tmp_path, sheet_name=sheet_name, dtype=str)
            return df
        finally:
            if os.path.exists(tmp_path):
                try:
                    os.remove(tmp_path)
                except Exception:
                    pass


def sync_metadata(engine: Engine, metrics: SyncMetrics, logger: logging.Logger) -> Tuple[int, int]:
    """Sync metadata from office server workbook into Supabase."""
    logger.info("=" * 60)
    logger.info("STEP 1: Synchronizing Clinical Metadata")
    logger.info("=" * 60)
    logger.info(f"Target Excel Path: {METADATA_EXCEL_PATH}")

    xl = pd.ExcelFile(METADATA_EXCEL_PATH)
    sheet_name = 'All Sample 2020 to till ' if 'All Sample 2020 to till ' in xl.sheet_names else xl.sheet_names[0]
    logger.info(f"Using Excel sheet: '{sheet_name}'")

    raw_df = read_excel_resilient(METADATA_EXCEL_PATH, sheet_name=sheet_name, logger=logger)
    metrics.meta_total_read = len(raw_df)
    logger.info(f"Read {len(raw_df)} total raw rows from Excel.")

    df = raw_df.loc[:, ~raw_df.columns.astype(str).str.startswith("Unnamed:")].copy()
    df.rename(columns=COL_MAP, inplace=True)

    # Ensure Study column uses RegisterType (only R&D and Biopharma)
    if 'RegisterType' in df.columns and not df['RegisterType'].isna().all():
        df['Study'] = df['RegisterType']
        df['PrimaryStudy'] = df['RegisterType']
    elif 'Study' in df.columns:
        df['PrimaryStudy'] = df['Study']
        df['RegisterType'] = df['Study']

    if 'FinalQualification' in df.columns:
        df['FinalQualification_Consolidated'] = df['FinalQualification']

    df['Sample_ID'] = df['Sample_ID'].astype(str).str.strip().replace({'nan': '', 'None': '', 'NaN': ''})
    df = df[df['Sample_ID'].ne('') & df['Sample_ID'].ne('Register')]

    for c in df.columns:
        df[c] = df[c].fillna('').astype(str).str.strip().replace({'nan': '', 'None': '', 'NaN': ''})

    with engine.connect() as conn:
        db_cols = [
            r[0] for r in conn.execute(text(
                "SELECT column_name FROM information_schema.columns "
                "WHERE table_name='metadata' ORDER BY ordinal_position"
            )).fetchall()
        ]

    for c in db_cols:
        if c not in df.columns:
            df[c] = ''
    df = df[db_cols]

    logger.info(f"Prepared {len(df)} standardized metadata rows across {df['Sample_ID'].nunique()} unique samples.")

    upserted_count = 0
    with engine.connect() as conn:
        for start in range(0, len(df), CHUNK_SIZE):
            chunk = df.iloc[start:start + CHUNK_SIZE]
            chunk_sids = chunk['Sample_ID'].unique().tolist()

            with conn.begin():
                conn.execute(
                    text('DELETE FROM "metadata" WHERE "Sample_ID" = ANY(:sids)'),
                    {'sids': chunk_sids}
                )
                chunk.to_sql('metadata', conn, if_exists='append', index=False)

            upserted_count += len(chunk)
            logger.info(f"  Upserted {upserted_count}/{len(df)} metadata records into Supabase...")

    metrics.meta_upserted = upserted_count
    logger.info(f"Successfully synchronized {upserted_count} metadata rows.")
    return upserted_count, df['Sample_ID'].nunique()
