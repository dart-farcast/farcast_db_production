# Farcast DB Production: Full Universal Setup & Usage Guide

I have successfully updated the `farcast_db_production` environment to be **100% Universal**. It will now handle Histopathology, Cytokine, and Flow Cytometry completely dynamically!

## 1. Folder Structure Overview

The production directory is located at: `c:\Users\somanath\farcast_db_claude\farcast_db_production`

Inside this folder, you will find 4 distinct components:
- `backend/`: The FastAPI Python backend (Port `5052`).
- `frontend/`: The React Dashboard (Port `5173`).
- `db_watcher/`: The active network monitoring and Quality Control script.
- `docker/`: The `docker-compose.yml` used to spin up your PostgreSQL instance.

---

## 2. How the Universal Logic Works

### The Universal DB Watcher (`db_watcher.py`)
- The watcher now monitors the entire root `\Assays` network drive.
- When a file drops in `\Assays\Cytokine` or `\Assays\Flow_Cytometry`, it automatically detects the folder name.
- It forces the file through the **Quality Control (QC) Gate**.
- **If it passes QC:** The watcher dynamically creates a brand new table in PostgreSQL (e.g., `assay_cytokine` or `assay_flow_cytometry`), appends any missing columns on the fly, upserts the data, and automatically triggers an API `/refresh` on the backend.
- **If it fails QC:** The file is instantly rejected, moved to a `QC_Failed/` subfolder inside that specific assay directory, and a `.txt` error log is generated.

### The Universal Backend (`data_loader.py`)
- The backend has been completely severed from the old local `.csv` files.
- At startup (and on auto-refresh), it queries PostgreSQL, discovers *every* table that starts with `assay_`, and dynamically loads them into memory.
- It parses names like `assay_flow_cytometry` into clean UI labels like `"Flow Cytometry"`.

---

## 3. How to Start the Environment

**Step 1: Start the Database**
1. Open terminal in `farcast_db_production\docker`
2. Run: `docker-compose up -d`

**Step 2: Start the DB Watcher**
1. Open terminal in `farcast_db_production\db_watcher`
2. Run: `python db_watcher.py`
*(The watcher will immediately crawl the Cytokine and Flow Cytometry folders and ingest all those historical files into Postgres!)*

**Step 3: Start the Backend API**
1. Open terminal in `farcast_db_production\backend`
2. Run: `python app.py`

**Step 4: View the Dashboard**
1. Open terminal in `farcast_db_production\frontend`
2. Run: `npm run dev` 
3. Navigate to `http://localhost:5173`.

Everything is completely automated. As the Data Science team drops new files for *any* assay, they will seamlessly appear in the dashboard moments later without ever needing to restart the servers.
