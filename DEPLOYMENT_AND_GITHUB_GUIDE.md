# FarCast DB v2 — Supabase, Railway & GitHub Deployment Guide

This guide details the exact steps to connect **Supabase Cloud PostgreSQL** with **Railway Live Hosting**, and how to push only the clean production database code to GitHub while keeping all temporary/scratch files excluded.

---

## 🛠️ PART 1: Steps to Connect Supabase and Railway

### Step 1: Set Up Supabase Cloud Database & Get Credentials
1. Go to [supabase.com](https://supabase.com) and log in.
2. Click **New Project** and name it `farcast-db-v2`.
3. Set a strong database password and select your preferred region.
4. Once the project is provisioned, go to **Project Settings $\rightarrow$ Database**:
   - Scroll down to **Connection string** and select **URI**.
   - Copy the URI: `postgresql://postgres:[YOUR-PASSWORD]@db.xxxx.supabase.co:5432/postgres` (replace `[YOUR-PASSWORD]` with your actual password).
5. Go to **Project Settings $\rightarrow$ API**:
   - Copy `Project URL` (e.g., `https://xxxx.supabase.co`)
   - Copy `anon public` key
   - Copy `service_role secret` key
6. Open the **SQL Editor** in Supabase:
   - Copy the entire SQL script from [`backend/database/schema.sql`](file:///c:/Users/somanath/farcast_db_production/backend/database/schema.sql).
   - Paste it into the SQL Editor and click **Run** to generate all tables, indexes, and initial whitelist rules.

---

### Step 2: Set Up Railway Live Hosting
1. Go to [railway.app](https://railway.app) and sign in with your GitHub account.
2. Click **New Project $\rightarrow$ Deploy from GitHub repo**.
3. Select your repository `farcast_db_production`.
4. In Railway, navigate to the **Variables** tab and click **Add Variable** to insert the credentials:
   - `SUPABASE_URL` = `https://xxxx.supabase.co`
   - `SUPABASE_KEY` = `your_anon_public_key`
   - `SUPABASE_SERVICE_ROLE_KEY` = `your_service_role_key`
   - `DATABASE_URL` = `postgresql://postgres:[PASSWORD]@db.xxxx.supabase.co:5432/postgres`
   - `JWT_SECRET` = `farcast_db_super_secret_jwt_key_production_2026_x89a`
   - `PORT` = `5052`
5. Railway will automatically detect the [`Dockerfile`](file:///c:/Users/somanath/farcast_db_production/Dockerfile), build the React frontend, package the FastAPI backend, and deploy your live site.
6. Under **Settings $\rightarrow$ Networking**, click **Generate Domain** to get your public live site URL (e.g., `https://farcast-db-v2-production.up.railway.app`).

---

## 📁 PART 2: Repository Segregation (What Gets Pushed vs. Ignored)

The [`.gitignore`](file:///c:/Users/somanath/farcast_db_production/.gitignore) file is configured so that **only** clean production code is tracked by Git.

### ✅ Production Files & Folders Pushed to GitHub:
```
farcast_db_production/
├── .github/
│   └── workflows/
│       └── deploy.yml           # CI/CD Automated Pipeline
├── backend/
│   ├── database/                # Isolated Database Layer
│   │   ├── schema.sql           # Supabase Cloud DDL
│   │   ├── db_client.py         # DB Connection Manager
│   │   ├── auth_db.py           # Auth & Whitelist Queries
│   │   └── data_loader.py       # Assay Ingestion & Indexing
│   ├── api/                     # FastAPI Routes & Auth
│   ├── app.py                   # Main FastAPI Entry Point
│   ├── requirements.txt         # Dependencies
│   └── locustfile.py            # Load Test Suite
├── frontend/                    # React Vite Frontend SPA
│   ├── src/
│   ├── package.json
│   └── vite.config.js
├── data/                        # Assay & Cohort Data
├── docker/                      # Docker Compose Config
├── Dockerfile                   # Railway Container Build
├── railway.json                 # Railway Cloud Config
├── .env.example                 # Environment Variable Template
├── .gitignore                   # Master Segregation Rules
└── README.md                    # Project Documentation
```

### ❌ Temporary & Non-Production Files Ignored (`.gitignore`):
- `.env` *(contains private API keys/passwords)*
- `*.db` & `auth.db` *(local SQLite databases)*
- `node_modules/` & `frontend/dist/` *(built dynamically)*
- `__pycache__/`, `*.log`, `locust_results_*`
- `arm_treatment_generater_code/` *(temporary scratch folder)*
- `cohort_todo/` & `cohort_todo2/` *(temporary work folders)*
- `cohort_data_files/`, `db_watcher/`, `docs_and_assets/`
- `histopathology_cohort_builder/`, `scripts/`
- `build_complete_mapping.py`, `investigate_root_causes.py`
- `requested_samples_treatment_details.csv`
- `DATA_TRACKING_README.md`, `farcast_production_resilience_plan.md`

---

## 📤 PART 3: Git Commands to Push to GitHub

Run these commands in your project root terminal to push only the clean, segregated files to GitHub:

```bash
# 1. Initialize Git (if not already initialized)
git init

# 2. Stage only the segregated files (respects .gitignore)
git add .

# 3. Check staged files to verify temporary files are excluded
git status

# 4. Commit the clean production codebase
git commit -m "Initial commit: FarCast DB v2 production database system with Supabase schema, isolated database module, and CI/CD"

# 5. Connect your remote GitHub repository
git remote add origin https://github.com/YOUR_GITHUB_USERNAME/farcast_db_production.git

# 6. Push to main branch
git branch -M main
git push -u origin main
```

Whenever you push new changes to `main`, Railway and the GitHub Actions CI/CD pipeline will automatically build and deploy to the live site.
