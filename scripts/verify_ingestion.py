import os
import glob
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

load_dotenv(r"c:\Users\somanath\farcast_db_production\.env")
db_url = os.environ.get("DATABASE_URL", "").strip().replace('postgresql://', 'postgresql+psycopg2://', 1)
engine = create_engine(db_url, connect_args={'connect_timeout': 15})

curated_dir = r"c:\Users\somanath\farcast_db_production\BP_shravan_curated_samples"
files = glob.glob(os.path.join(curated_dir, "**", "*.xlsx"), recursive=True)
files = [f for f in files if not os.path.basename(f).startswith("~$") and not os.path.basename(f).startswith("._")]
sids = sorted(list(set(os.path.basename(f).split('.')[0].split('_')[0].strip() for f in files)))

with engine.connect() as conn:
    total_in_db = conn.execute(text('SELECT count(*) FROM "assay_histopathology"')).scalar()
    curated_in_db = conn.execute(
        text('SELECT count(*) FROM "assay_histopathology" WHERE "Sample_ID" = ANY(:sids)'),
        {'sids': sids}
    ).scalar()
    samples_with_data = conn.execute(
        text('SELECT count(DISTINCT "Sample_ID") FROM "assay_histopathology" WHERE "Sample_ID" = ANY(:sids)'),
        {'sids': sids}
    ).scalar()
    
    print("=" * 60)
    print("VERIFICATION IN SUPABASE:")
    print("  Total rows in assay_histopathology :", total_in_db)
    print(f"  Curated rows in database          : {curated_in_db} (expected: 1,602)")
    print(f"  Curated samples in database       : {samples_with_data} / {len(sids)}")
    
    # Check sample rows
    print("\nSample records for FBB1B210071:")
    rows = conn.execute(text('SELECT * FROM "assay_histopathology" WHERE "Sample_ID" = \'FBB1B210071\' LIMIT 2')).fetchall()
    for r in rows:
        print(dict(r._mapping))

    # Check CD8 sample
    print("\nSample records for FBB1H230111 (with CD8):")
    rows = conn.execute(text('SELECT "Sample_ID", "Arms", "Intratumoral_CD8", "Stromal_CD8", "Necrosis_Score", "Ki67", "Cas-3" FROM "assay_histopathology" WHERE "Sample_ID" = \'FBB1H230111\' AND "Intratumoral_CD8" != \'\' LIMIT 2')).fetchall()
    for r in rows:
        print(dict(r._mapping))
    print("=" * 60)
