"""
FarCast DB v2 — Data Loader Module
Direct Database Loader: Loads multi-omics assay data, metadata, and overlay exclusively from PostgreSQL (Supabase Cloud).
No local file fallbacks.
"""
import os
import pandas as pd
from sqlalchemy import create_engine, inspect, text

SID_ALIASES = ['sample_id', 'sampleid', 'sample id', 'register']
ARM_ALIASES = ['arms', 'arm', 'arm_code', 'treatment arms']

KNOWN_ASSAYS = {
    'assay_histopathology': 'Histopathology',
    'assay_cytokine':       'Cytokine Release Assay',
    'assay_nanostring':     'NanoString',
    'assay_mihc':           'mIHC'
}


def clean_df(df: pd.DataFrame) -> pd.DataFrame:
    df = df.loc[:, ~df.columns.str.startswith('Unnamed:')]
    df.columns = df.columns.str.strip().str.replace('\n', ' ')
    for c in df.select_dtypes('object').columns:
        df[c] = df[c].str.strip()
    return df.fillna('')


def clean_drug_value(d, arm_code='') -> str:
    """Filter out unmapped arm codes (RXA, RXB, ARM1) and remarks/notes from drug values."""
    if not d or pd.isna(d):
        return ''
    d_clean = str(d).strip()
    d_upper = d_clean.upper()
    if any(phrase in d_upper for phrase in [
        'NOT MENTIONED', 'MISSED DETAILS', 'INSERT STUDY', 'TX RECEIVED WITH', 'DRUG DETAILS'
    ]):
        return ''
    if d_upper.startswith('ARM') or d_upper.startswith('RX'):
        return ''
    return d_clean


def is_sample_qualified(val) -> bool:
    """Determine if sample is qualified based on Final Qualification column."""
    if not val or pd.isna(val):
        return False
    v = str(val).strip().lower()
    if any(rej in v for rej in ('reject', 'compromised', 'contaminat', 'terminated', 'invalid', 'low tumor')):
        return False
    return v == 'qualified' or 'passed' in v


def find_col(df: pd.DataFrame, aliases: list):
    for c in df.columns:
        if c.strip().lower() in aliases:
            return c
    return None


def get_db_engine():
    db_url = os.environ.get('DATABASE_URL', '').strip()
    if not db_url:
        raise ValueError("DATABASE_URL is not configured in environment.")
    if db_url.startswith('postgres://'):
        db_url = db_url.replace('postgres://', 'postgresql://', 1)
    return create_engine(db_url, connect_args={'connect_timeout': 15})


def load_metadata() -> pd.DataFrame:
    """Load metadata table strictly from PostgreSQL database."""
    try:
        engine = get_db_engine()
        insp = inspect(engine)
        if insp.has_table('metadata'):
            df = pd.read_sql_table('metadata', engine)
            if not df.empty and 'Sample_ID' in df.columns:
                print(f"  Successfully loaded {len(df)} metadata rows from Database.")
                df = clean_df(df)
                if 'Study' in df.columns and 'RegisterType' not in df.columns:
                    df['RegisterType'] = df['Study']
                return df
        else:
            print("  [Metadata Loader] Table 'metadata' not found in Database.")
    except Exception as e:
        print(f"  [Metadata Loader Error] Failed loading metadata from Database: {e}")
    return pd.DataFrame()


def build_overlay() -> pd.DataFrame:
    """Load overlay table strictly from PostgreSQL database."""
    try:
        engine = get_db_engine()
        insp = inspect(engine)
        if insp.has_table('overlay'):
            df = pd.read_sql_table('overlay', engine)
            if not df.empty and 'Sample_ID' in df.columns:
                print(f"  Successfully loaded {len(df)} overlay rows from Database.")
                df = clean_df(df)
                if 'Drug' in df.columns:
                    df['Drug'] = df['Drug'].apply(clean_drug_value)
                return df
        else:
            print("  [Overlay Loader] Table 'overlay' not found in Database.")
    except Exception as e:
        print(f"  [Overlay Loader Error] Failed loading overlay from Database: {e}")
    return pd.DataFrame(columns=['Sample_ID', 'Position', 'Arm_Code', 'Drug'])


def load_assay_dfs(assay_paths: dict = None) -> dict:
    """Load all assay tables strictly from PostgreSQL database."""
    dfs = {}
    try:
        engine = get_db_engine()
        insp = inspect(engine)
        all_tables = set(insp.get_table_names())
        try:
            all_tables.update(insp.get_table_names(schema='public'))
        except Exception:
            pass

        def _get_assay_name(tbl_str: str) -> str:
            tbl_clean = tbl_str.lower().strip()
            if tbl_clean in KNOWN_ASSAYS:
                return KNOWN_ASSAYS[tbl_clean]
            for k, v in KNOWN_ASSAYS.items():
                if k.replace('assay_', '') in tbl_clean:
                    return v
            return tbl_str.replace('assay_', '').replace('_', ' ').title()

        for table in all_tables:
            if table.startswith('assay_'):
                name = _get_assay_name(table)
                try:
                    df = pd.read_sql_query(text(f'SELECT * FROM "{table}"'), engine)
                    if not df.empty:
                        dfs[name] = clean_df(df)
                        print(f"  Successfully loaded {len(df)} rows for {name} from Database.")
                except Exception as err:
                    print(f"  [Assay Loader Error] Failed querying {table}: {err}")

        for tbl, name in KNOWN_ASSAYS.items():
            if name not in dfs:
                try:
                    df = pd.read_sql_query(text(f'SELECT * FROM "{tbl}"'), engine)
                    if not df.empty:
                        dfs[name] = clean_df(df)
                        print(f"  Successfully loaded {len(df)} rows for {name} from Database.")
                except Exception:
                    pass

    except Exception as e:
        print(f"  [Assay Loader Error] Database connection failed: {e}")

    return dfs


def build_assay_presence_map(assay_dfs: dict) -> dict:
    presence = {}
    for name, df in assay_dfs.items():
        sid_col = find_col(df, SID_ALIASES)
        if not sid_col:
            continue
        for sid in df[sid_col].str.strip().unique():
            if sid:
                presence.setdefault(sid, [])
                if name not in presence[sid]:
                    presence[sid].append(name)
    return presence


def compute_stats(meta: pd.DataFrame, overlay: pd.DataFrame, assay_dfs: dict) -> dict:
    drugs     = overlay['Drug'].replace('', pd.NA).dropna() if not overlay.empty and 'Drug' in overlay.columns else pd.Series(dtype=object)
    study_col = 'Study' if 'Study' in meta.columns else ('RegisterType' if 'RegisterType' in meta.columns else None)
    indications = (meta['CancerType'].replace('', pd.NA).dropna().value_counts().to_dict()
                   if 'CancerType' in meta.columns else {})
    study_list = (sorted(meta[study_col].replace('', pd.NA).dropna().unique().tolist())
                  if study_col else [])
    a_samples = {}
    for name, df in assay_dfs.items():
        sid_col = find_col(df, SID_ALIASES)
        a_samples[name] = int(df[sid_col].replace('', pd.NA).dropna().nunique()) if sid_col and sid_col in df.columns else 0

    total_samples = int(meta['Sample_ID'].nunique()) if not meta.empty and 'Sample_ID' in meta.columns else 0

    # Qualification Breakdown
    qual_col = next((c for c in ['FinalQualification', 'Final Qualification', 'Final_Qualification'] if c in meta.columns), None)
    if qual_col and not meta.empty:
        is_qual_mask = meta[qual_col].apply(is_sample_qualified)
        qualified_samples = int(meta[is_qual_mask]['Sample_ID'].nunique())
    else:
        is_qual_mask = pd.Series(True, index=meta.index) if not meta.empty else pd.Series(dtype=bool)
        qualified_samples = total_samples

    disqualified_samples = max(0, total_samples - qualified_samples)

    # R&D vs BioPharma stats
    rd_mask = meta[study_col].astype(str).str.strip().str.lower().isin(['r&d', 'internal r&d']) if study_col and not meta.empty else pd.Series(False, index=meta.index)
    bio_mask = meta[study_col].astype(str).str.strip().str.lower().isin(['biopharma', 'bio pharma']) if study_col and not meta.empty else pd.Series(False, index=meta.index)

    internal_rd_total = int(meta[rd_mask]['Sample_ID'].nunique()) if not meta.empty else 0
    internal_rd_qualified = int(meta[rd_mask & is_qual_mask]['Sample_ID'].nunique()) if not meta.empty and qual_col else 0

    biopharma_total = int(meta[bio_mask]['Sample_ID'].nunique()) if not meta.empty else 0
    biopharma_qualified = int(meta[bio_mask & is_qual_mask]['Sample_ID'].nunique()) if not meta.empty and qual_col else 0

    return {
        'samples':                total_samples,
        'qualified_samples':      qualified_samples,
        'disqualified_samples':   disqualified_samples,
        'internal_rd_total':      internal_rd_total,
        'internal_rd_qualified':  internal_rd_qualified,
        'biopharma_total':        biopharma_total,
        'biopharma_qualified':    biopharma_qualified,
        'drugs':                  int(drugs.nunique()) if not drugs.empty else 0,
        'assay_samples':          a_samples,
        'studies':                int(meta[study_col].nunique()) if study_col and not meta.empty else 0,
        'indications':            indications,
        'top_drugs':              drugs.value_counts().head(20).index.tolist() if not drugs.empty else [],
        'study_list':             study_list,
    }


def build_indexes(meta: pd.DataFrame, overlay: pd.DataFrame) -> dict:
    """Pre-build {value: set(sample_ids)} for fast multi-select search."""
    drug_index   = {}
    arm_index    = {}
    cancer_index = {}
    study_index  = {}
    site_index   = {}
    project_index = {}

    for _, row in overlay.iterrows():
        d = row['Drug'].strip()
        a = row['Arm_Code'].strip().upper()
        s = row['Sample_ID']
        if d:
            drug_index.setdefault(d.lower(), set()).add(s)
        if a:
            arm_index.setdefault(a.lower(), set()).add(s)

    for col, idx in [('CancerType', cancer_index), ('Study', study_index),
                     ('TumorSite', site_index),    ('Project_ID', project_index)]:
        if col not in meta.columns:
            continue
        for _, row in meta.iterrows():
            v = row[col].strip()
            s = row['Sample_ID']
            if v:
                idx.setdefault(v.lower(), set()).add(s)

    all_sids = set(meta['Sample_ID'].unique()) if not meta.empty and 'Sample_ID' in meta.columns else set()
    qual_col = next((c for c in ['FinalQualification', 'Final Qualification', 'Final_Qualification'] if c in meta.columns), None)
    if qual_col and not meta.empty:
        qual_mask = meta[qual_col].apply(is_sample_qualified)
        qualified_sids = set(meta[qual_mask]['Sample_ID'].unique())
    else:
        qualified_sids = all_sids.copy()

    return {
        'drug':           drug_index,
        'arm':            arm_index,
        'cancer':         cancer_index,
        'study':          study_index,
        'site':           site_index,
        'project':        project_index,
        'all_sids':       all_sids,
        'qualified_sids': qualified_sids,
    }
