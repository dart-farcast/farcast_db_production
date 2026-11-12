# Histopathology Data Ingestion Guide
## FarCast DB v2 — Self-Service Ingestion Workflow

This guide details how to ingest new Histopathology master data files into the Supabase Cloud database (`assay_histopathology`) at any time without needing AI assistance.

---

### Method 1: One-Click Execution (Windows)

A launcher script has been created in the repository root:
[`run_histopathology_ingestion.bat`](file:///c:/Users/somanath/farcast_db_production/run_histopathology_ingestion.bat)

1. **Default Ingestion** (`BP_shravan_curated_samples`):
   - Double-click [`run_histopathology_ingestion.bat`](file:///c:/Users/somanath/farcast_db_production/run_histopathology_ingestion.bat) and press `Enter`.
   - The script will scan, parse, validate, and upload all `.xlsx` files into Supabase.

2. **Ingest a Different Folder**:
   - Double-click [`run_histopathology_ingestion.bat`](file:///c:/Users/somanath/farcast_db_production/run_histopathology_ingestion.bat).
   - When prompted: `Enter the folder path containing the Excel masterfiles`, paste or type your new folder path (e.g. `C:\Users\somanath\Desktop\New_Histo_Files`) and press `Enter`.
   - *Tip:* You can also drag and drop a folder directly onto `run_histopathology_ingestion.bat` in Windows File Explorer!

---

### Method 2: Command-Line Execution (PowerShell or Command Prompt)

Open a terminal in `c:\Users\somanath\farcast_db_production` and run:

#### 1. Ingest the default curated directory:
```powershell
python scripts/ingest_histopathology.py
```

#### 2. Ingest a specific directory of Excel files:
```powershell
python scripts/ingest_histopathology.py --dir "C:\path\to\your\excel_folder"
```

#### 3. Ingest a single file:
```powershell
python scripts/ingest_histopathology.py --file "C:\path\to\sample.xlsx"
```

#### 4. Dry Run (Test and preview without changing the database):
```powershell
python scripts/ingest_histopathology.py --dry-run
```

---

### How the Ingestion Script Works

1. **Recursive Scan**:
   - Recursively discovers all `.xlsx` files in the target directory and subdirectories.
   - Automatically ignores temporary files (e.g., files beginning with `~$` or `._`).

2. **Automated Sheet & Sample Recognition**:
   - Looks for the sheet named `'Master'` (case-insensitive).
   - If no Master sheet is found, it automatically detects sheets containing an `'Arms'` or `'Arm'` column.
   - Extracts the `Sample_ID` from the table or from the filename prefix (e.g. `FBB1B210071.xlsx...` $\rightarrow$ `FBB1B210071`).

3. **Data Normalization & Cleaning**:
   - Normalizes Arm nomenclature (`Rx-A` $\rightarrow$ `RXA`, `Arm-1` $\rightarrow$ `ARM1`).
   - Normalizes column names (e.g., `Necrosis_score` $\rightarrow$ `Necrosis_Score`, `Ki67`, `Cas-3`).
   - Maps CD8 quantification columns (`Tumoral_CD8_count` $\rightarrow$ `Intratumoral_CD8`, `Stromal_CD8_count` $\rightarrow$ `Stromal_CD8`).
   - Cleans integers (e.g. `1.0` $\rightarrow$ `'1'`, empty cells $\rightarrow$ `''`).

4. **Safe Upsert**:
   - Deletes prior records for only the incoming `Sample_ID`s to prevent duplicate entries.
   - Batches new rows into chunks of 500 rows and commits them to Supabase Cloud PostgreSQL.

5. **Instant In-Memory Cache Reload**:
   - Contacts the local backend server (`http://localhost:5052/api/refresh`) to instantly refresh the in-memory cache so dashboards reflect new counts without requiring a server restart.

---

### Verification

To verify the state of `assay_histopathology` in Supabase at any time:
```powershell
python scripts/verify_ingestion.py
```
This queries Supabase Cloud directly and reports total records, unique samples, and prints sample rows.
