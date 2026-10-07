import os
import pandas as pd
from sqlalchemy import create_engine, text

DEFAULT_DB_URL = "postgresql://postgres.nviuiklcusydkxoctlsj:farcast2026@aws-0-ap-northeast-1.pooler.supabase.com:5432/postgres"
EXCEL_PATH = r"c:\Users\somanath\farcast_db_production\Sample Metrics Sheet_Pathology details_ Images, Score & Block Details_017 to 2020_Updated on 25Sep2026_Updated_20260928_153848.xlsx"

def main():
    print(f"Loading Master Sheet from: {EXCEL_PATH}")
    df = pd.read_excel(EXCEL_PATH, sheet_name="Master Sheet")
    print(f"Raw shape: {df.shape}")
    
    # Drop completely empty columns / unnamed columns
    cols_to_keep = [c for c in df.columns if not str(c).startswith('Unnamed:')]
    df = df[cols_to_keep]
    
    # Drop rows without MBT
    df = df.dropna(subset=['MBT'])
    print(f"Valid rows with MBT: {len(df)}")
    
    # Clean column names for SQL
    col_mapping = {
        'S.No.': 's_no',
        'Year ': 'year',
        'Year': 'year',
        'Month': 'month',
        'Date': 'collection_date',
        'MBT': 'mbt',
        'Study Name': 'study_name',
        'Study 1': 'study_1',
        'Study 2': 'study_2',
        'Cancer Type': 'cancer_type',
        'Main Cancer Types': 'main_cancer_type',
        'Primary Study': 'primary_study',
        'Physician': 'physician',
        'Hospital': 'hospital',
        'Relationship Name': 'relationship_name',
        'Type of Relationship': 'type_of_relationship',
        'Age': 'age',
        'Gender': 'gender',
        'pTNM': 'ptnm',
        'Type of procedure': 'procedure_type',
        'Sample Type': 'sample_type',
        'FFPE Block Availability': 'ffpe_block_availability',
        'T0 Images ': 't0_images',
        'T0 Images': 't0_images',
        'Markers': 'markers_t0',
        'T72 Images': 't72_images',
        'Markers2': 'markers_t72',
        'T0 Score': 't0_score',
        'T72 Score': 't72_score',
        'Final Qualification': 'final_qualification',
        'final qualification': 'final_qualification',
        'Qualification Status': 'qualification_status',
        'Comments': 'comments',
        'Column3': 'column3'
    }
    
    df = df.rename(columns={k: v for k, v in col_mapping.items() if k in df.columns})
    
    if 'final_qualification' not in df.columns:
        df['final_qualification'] = ''
    
    # Format fields as strings / clean nulls
    for c in df.columns:
        if c == 'collection_date':
            df[c] = pd.to_datetime(df[c], errors='coerce').dt.strftime('%Y-%m-%d').fillna('')
        elif c in ['year', 's_no']:
            df[c] = pd.to_numeric(df[c], errors='coerce').fillna(0).astype(int).astype(str).replace('0', '')
        else:
            df[c] = df[c].astype(str).str.strip().replace({'nan': '', 'None': '', 'NaT': '', 'NaN': ''})

    # Move '1st level attrition' from primary_study to qualification_status and set primary_study to 'NA'
    attrition_mask = df['primary_study'].astype(str).str.strip().str.lower() == '1st level attrition'
    df.loc[attrition_mask, 'qualification_status'] = '1st level attrition'
    df.loc[attrition_mask, 'primary_study'] = 'NA'
    
    engine = create_engine(DEFAULT_DB_URL)
    with engine.begin() as conn:
        print("Creating table pre_reboot_metadata in Supabase...")
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS pre_reboot_metadata (
                id SERIAL PRIMARY KEY,
                s_no TEXT,
                year TEXT,
                month TEXT,
                collection_date TEXT,
                mbt TEXT,
                study_name TEXT,
                study_1 TEXT,
                study_2 TEXT,
                cancer_type TEXT,
                main_cancer_type TEXT,
                primary_study TEXT,
                physician TEXT,
                hospital TEXT,
                relationship_name TEXT,
                type_of_relationship TEXT,
                age TEXT,
                gender TEXT,
                ptnm TEXT,
                procedure_type TEXT,
                sample_type TEXT,
                ffpe_block_availability TEXT,
                t0_images TEXT,
                markers_t0 TEXT,
                t72_images TEXT,
                markers_t72 TEXT,
                t0_score TEXT,
                t72_score TEXT,
                qualification_status TEXT,
                final_qualification TEXT,
                comments TEXT,
                column3 TEXT
            );
            
            TRUNCATE TABLE pre_reboot_metadata;
            CREATE INDEX IF NOT EXISTS idx_pre_reboot_mbt ON pre_reboot_metadata(mbt);
            CREATE INDEX IF NOT EXISTS idx_pre_reboot_cancer ON pre_reboot_metadata(main_cancer_type);
            CREATE INDEX IF NOT EXISTS idx_pre_reboot_year ON pre_reboot_metadata(year);
            CREATE INDEX IF NOT EXISTS idx_pre_reboot_study ON pre_reboot_metadata(primary_study);
            CREATE INDEX IF NOT EXISTS idx_pre_reboot_hospital ON pre_reboot_metadata(hospital);
            CREATE INDEX IF NOT EXISTS idx_pre_reboot_qual ON pre_reboot_metadata(qualification_status);
            CREATE INDEX IF NOT EXISTS idx_pre_reboot_final_qual ON pre_reboot_metadata(final_qualification);
        """))
    
    print("Ingesting rows in batches...")
    df.to_sql('pre_reboot_metadata', engine, if_exists='append', index=False, chunksize=1000, method='multi')
    
    with engine.connect() as conn:
        cnt = conn.execute(text("SELECT count(*) FROM pre_reboot_metadata")).scalar()
        print(f"SUCCESS! Total rows in pre_reboot_metadata: {cnt}")

if __name__ == "__main__":
    main()
