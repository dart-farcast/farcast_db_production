"""
FarCast DB v2 — Data Loader Module
Isolated Data I/O: Ingests multi-omics assay data & metadata from PostgreSQL (Supabase/Local) or Excel/CSV.
"""
import os, re
import pandas as pd

# ── Path resolution ─────────────────────────────────────────────────────────────
_HERE        = os.path.dirname(os.path.abspath(__file__))
DATA_DIR     = os.path.normpath(os.path.join(_HERE, '..', '..', 'data'))
COHORT_DIR   = os.path.join(DATA_DIR, 'latest cohort data')
COHORT_FILE  = os.path.join(COHORT_DIR, 'All sample details_Till July 2026_Satish (1).xlsx')
COHORT_SHEET = 'All Sample 2020 to till Jun2026'
CORE_FILES   = {'arm_table.csv', 'treatment_table.csv', 'metadata_table.csv'}
SID_ALIASES  = ['sample_id', 'sampleid', 'sample id', 'register']
ARM_ALIASES  = ['arms', 'arm', 'arm_code', 'treatment arms']

COHORT_COL_MAP = {
    'Register':                            'Sample_ID',
    'CASE No':                             'CaseNo',
    'Register Type':                       'Study',             # Mapped to Study Type
    'Sample Collection Date':              'CollectionDate',
    'Sample Collection Date\n(dd-mm-yyyy)': 'CollectionDate',
    'Protocol':                            'Protocol',
    'Patient ID':                          'PatientID',
    'Project':                             'Project_ID',        # Study Code
    'Primary study':                       'PrimaryStudy',
    'Tissue Qualification':                'TissueQualification',
    'Blood Qualification':                 'BloodQualification',
    'Baseline Qualification':              'BaselineQualification',
    'Final Qualification':                 'FinalQualification',
    'Reason':                              'Reason',
    'Tumor Status':                        'TumorStatus',
    'Type of relationship':                'TypeOfRelationship',
    'Hospital':                            'Hospital',
    'Hospital Address':                    'HospitalAddress',
    'Physican':                            'Physician',
    'Cancer Type':                         'CancerType',
    'Cancer Sub Type':                     'CancerSubType',
    'Tumor Site':                          'TumorSite',
    'Tumor Site Details':                  'TumorSiteDetails',
    'Gender':                              'Gender',
    'Age':                                 'Age',
    'Infection Status':                    'InfectionStatus',
    'Temp':                                'Temperature',
    'Temprature':                          'Temperature',
    'Logistic':                            'Logistic',
    'Procedure Type':                      'ProcedureType',
    'Sample Type':                         'SampleType',
    'Therapy':                             'Therapy',
    'cTNM':                                'cTNM',
    'Cancer Stage':                        'CancerStage',
    'Cancer Stage-1':                      'CancerStage',
    'Cancer Grade':                        'CancerGrade',
    'pTNM':                                'pTNM',
    'Treatment Cycles':                    'TreatmentCycles',
    'Drug Name':                           'DrugName',
    'Histopath':                           'Histopath',
    'Post Surgery Treatment Arms':         'PostSurgeryTreatmentArms',
    'Post Surgery Drug Name':              'PostSurgeryDrugName',
    'Sample Processing Date':              'ProcessingDate',
    'Tissue Size pre processing (in cm)':  'TissueSizePreProcessing',
    'Tissue size post processing':         'TissueSizePostProcessing',
    'Explant Size':                        'ExplantSize',
    'Room #':                              'RoomNumber',
    'Processed By':                        'ProcessedBy',
    'Blood qualified (Y/N)':               'BloodQualifiedYN',
    'Autologus Plasma Addition (Y/N)':     'AutologusPlasmaAddition',
    'Autologus Serum Addition (Y/N)':      'AutologusSerumAddition',
    'Co-culture':                          'CoCulture',
    'Q2 Qualification':                    'Q2Qualification',
    'Reason for Q2':                       'ReasonForQ2',
    'T0 - M/V T0(Arm x Replicates)':      'T0_MV',
    'Culture - M/V Tx (Arm x Replicates)': 'Culture_MVTx',
    'Total # of explants':                 'TotalExplants',
    'Q2.5 Qualifiction':                   'Q2_5_Qualification',
    'Q3 Qualification based on Pathology (>10% tumor content of 5 out of 7 at T0 and all arms of T72) (By Ritu)': 'Q3_Qualification',
    'Q4 Qualification':                    'Q4_Qualification',
    'Final Qualification.1':               'FinalQualification_Consolidated',
    'Remarks':                             'Remarks',
}

def rcsv(path: str) -> pd.DataFrame:
    try:
        df = pd.read_csv(path, dtype=str, encoding='utf-8')
    except UnicodeDecodeError:
        df = pd.read_csv(path, dtype=str, encoding='latin1')
    df.columns = df.columns.str.strip().str.replace('\n', ' ')
    for c in df.select_dtypes('object').columns:
        df[c] = df[c].str.strip()
    return df.fillna('')

def rxlsx(path: str, sheet=0) -> pd.DataFrame:
    df = pd.read_excel(path, sheet_name=sheet, dtype=str)
    df.columns = df.columns.str.strip().str.replace('\n', ' ')
    for c in df.select_dtypes('object').columns:
        df[c] = df[c].str.strip()
    return df.fillna('')

def find_col(df: pd.DataFrame, aliases: list):
    for c in df.columns:
        if c.strip().lower() in aliases:
            return c
    return None

def arm_position_cols(df: pd.DataFrame) -> list:
    skip = {'sample_id', 'indication', 'project_id'}
    return [c for c in df.columns if c.lower() not in skip and c.strip()]

def clean_df(df: pd.DataFrame) -> pd.DataFrame:
    df = df.loc[:, ~df.columns.str.startswith('Unnamed:')]
    df.columns = df.columns.str.strip().str.replace('\n', ' ')
    for c in df.select_dtypes('object').columns:
        df[c] = df[c].str.strip()
    return df.fillna('')

def is_sample_qualified(val) -> bool:
    """Determine if sample is qualified based on Final Qualification column."""
    if not val or pd.isna(val):
        return False
    v = str(val).strip().lower()
    if any(rej in v for rej in ('reject', 'compromised', 'contaminat', 'terminated', 'invalid', 'low tumor')):
        return False
    return v == 'qualified' or 'passed' in v

def load_metadata() -> pd.DataFrame:
    db_url = os.environ.get('DATABASE_URL', '').strip()
    if db_url:
        try:
            from sqlalchemy import create_engine, inspect
            engine = create_engine(db_url, connect_args={'connect_timeout': 5})
            insp = inspect(engine)
            if insp.has_table('metadata'):
                df = pd.read_sql_table('metadata', engine)
                if not df.empty and 'Sample_ID' in df.columns:
                    print(f"  Successfully loaded {len(df)} metadata rows from Supabase Cloud.")
                    df = clean_df(df)
                    if 'Study' in df.columns and 'RegisterType' not in df.columns:
                        df['RegisterType'] = df['Study']
                    return df
        except Exception as e:
            print(f"  [Metadata Loader Note] Supabase metadata fallback: {e}")

    # Fallback to local excel
    if os.path.exists(COHORT_FILE):
        df = pd.read_excel(COHORT_FILE, sheet_name=COHORT_SHEET, dtype=str)
        # Drop empty trailing rows
        if 'Register' in df.columns:
            df = df.dropna(subset=['Register'])
        elif 'Sample_ID' in df.columns:
            df = df.dropna(subset=['Sample_ID'])
        for c in df.select_dtypes('object').columns:
            df[c] = df[c].str.strip()
        renames = {k: v for k, v in COHORT_COL_MAP.items() if k in df.columns}
        df = df.rename(columns=renames)
        df = df.loc[:, ~df.columns.str.startswith('Unnamed:')]
        if 'Sample_ID' in df.columns:
            df = df[df['Sample_ID'].str.strip().ne('')]
            df = df.drop_duplicates(subset=['Sample_ID'], keep='first')
        if 'Study' in df.columns and 'RegisterType' not in df.columns:
            df['RegisterType'] = df['Study']
        return df.fillna('')
    return pd.DataFrame()

def resolve_file(filename, fallback_patterns):
    path = os.path.join(DATA_DIR, filename)
    if os.path.exists(path):
        return path
    import glob
    for d in [DATA_DIR, COHORT_DIR]:
        for pat in fallback_patterns:
            matches = glob.glob(os.path.join(d, pat))
            if matches:
                return matches[0]
    return None

def build_overlay() -> pd.DataFrame:
    db_url = os.environ.get('DATABASE_URL', '').strip()
    if db_url:
        try:
            from sqlalchemy import create_engine, inspect
            engine = create_engine(db_url, connect_args={'connect_timeout': 5})
            insp = inspect(engine)
            if insp.has_table('overlay'):
                df = pd.read_sql_table('overlay', engine)
                if not df.empty and 'Sample_ID' in df.columns:
                    print(f"  Successfully loaded {len(df)} overlay rows from Supabase Cloud.")
                    return clean_df(df)
        except Exception as e:
            print(f"  [Overlay Loader Note] Supabase overlay fallback: {e}")

    # Fallback to local csv
    arm_path = resolve_file('arm_table.csv', ['*arm_table*.csv', '*arm_table*.xlsx'])
    trt_path = resolve_file('treatment_table.csv', ['*treatment_table*.csv', '*treatment_table*.xlsx'])

    if not arm_path or not os.path.exists(arm_path):
        print("  WARNING: arm_table.csv not found for overlay.")
        return pd.DataFrame(columns=['Sample_ID', 'Position', 'Arm_Code', 'Drug'])

    arm = rcsv(arm_path) if arm_path.endswith('.csv') else rxlsx(arm_path)
    trt = (rcsv(trt_path) if trt_path.endswith('.csv') else rxlsx(trt_path)) if trt_path else pd.DataFrame()

    pos_cols = arm_position_cols(arm)
    rows = []
    for _, ar in arm.iterrows():
        sid = ar.get('Sample_ID', '').strip()
        if not sid:
            continue
        tr  = trt[trt['Sample_ID'] == sid] if not trt.empty and 'Sample_ID' in trt.columns else pd.DataFrame()
        for pos in pos_cols:
            code = str(ar.get(pos, '')).strip()
            if not code or code.lower() in ('nan', 'none'):
                continue
            drug = ''
            if not tr.empty and pos in tr.columns:
                drug = str(tr.iloc[0][pos]).strip()
                if drug.lower() in ('nan', 'none'):
                    drug = ''
            rows.append({'Sample_ID': sid, 'Position': pos,
                         'Arm_Code': code.upper(), 'Drug': drug})
    return (pd.DataFrame(rows) if rows
            else pd.DataFrame(columns=['Sample_ID', 'Position', 'Arm_Code', 'Drug']))


def load_assay_dfs(assay_paths: dict = None) -> dict:
    """Return {name: DataFrame} for every assay table in PostgreSQL (Cloud/Local) or fallback files."""
    dfs = {}
    db_url = os.environ.get('DATABASE_URL', '').strip()
    if db_url.startswith('postgres://'):
        db_url = db_url.replace('postgres://', 'postgresql://', 1)

    if db_url:
        try:
            from sqlalchemy import create_engine, inspect, text
            engine = create_engine(db_url, connect_args={'connect_timeout': 8})
            insp = inspect(engine)
            
            # 1. Discover all tables with assay_ prefix across default & public schemas
            all_tables = set(insp.get_table_names())
            try:
                all_tables.update(insp.get_table_names(schema='public'))
            except Exception:
                pass

            # Known assay tables mapping
            KNOWN_ASSAYS = {
                'assay_histopathology': 'Histopathology',
                'assay_cytokine':       'Cytokine',
                'assay_nanostring':     'Nanostring',
                'assay_mihc':           'Mihc'
            }

            for table in all_tables:
                if table.startswith('assay_'):
                    name = table.replace('assay_', '').replace('_', ' ').title()
                    try:
                        df = pd.read_sql_query(text(f'SELECT * FROM "{table}"'), engine)
                        if not df.empty:
                            dfs[name] = clean_df(df)
                            print(f"  Successfully loaded {len(df)} rows for {name} from Supabase.")
                    except Exception as err:
                        print(f"  [Table Query Note] Error reading {table}: {err}")

            # Also try any known table not found in discovery
            for tbl, name in KNOWN_ASSAYS.items():
                if name not in dfs:
                    try:
                        df = pd.read_sql_query(text(f'SELECT * FROM "{tbl}"'), engine)
                        if not df.empty:
                            dfs[name] = clean_df(df)
                            print(f"  Successfully loaded {len(df)} rows for {name} from Supabase.")
                    except Exception:
                        pass

        except Exception as e:
            print(f"  [Assay Loader Note] PostgreSQL assay connection note: {e}")

    # Fallback to local files if database is offline or returned 0 assays
    if not dfs:
        print("  [Assay Loader Fallback] Loading assays from local cohort data files...")
        local_mapping = {
            'Histopathology': ['06Aug2026_histo_cohort.xlsx', '22Jul2026_histo_cohort.xlsx'],
            'Cytokine':       ['Cytokine_cohort_1_fixed.xlsx'],
            'Nanostring':     ['Nanostring_currated_data.xlsx'],
            'Mihc':           ['mIHC image details With Treatment Details_SS 1.xlsx'],
        }
        for name, files in local_mapping.items():
            for f in files:
                p = os.path.join(COHORT_DIR, f)
                if os.path.exists(p):
                    try:
                        dfs[name] = clean_df(rxlsx(p))
                        print(f"  Fallback loaded {len(dfs[name])} rows for {name} from {f}")
                        break
                    except Exception as err:
                        print(f"  Failed local fallback for {name}: {err}")

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
