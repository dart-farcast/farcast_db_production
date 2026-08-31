# Farcast Biosciences Database Portal & Platform

Welcome to the nccaa ca**Farcast Biosciences Database Portal** codebase repository.

---

## 📚 Core Navigation & Tracking Documentation

* 📊 **[Master Data &amp; Sample Tracking README](file:///c:/Users/somanath/farcast_db_production/DATA_TRACKING_README.md):** Complete inventory of all 996 tissue samples, 135 studies, 395 unique drugs, assay coverage (mIHC, NanoString, Histopathology), and cancer indication sample breakdowns.
* 🧬 **[Histopathology Cohort Builder Tool &amp; SOP](file:///c:/Users/somanath/farcast_db_production/histopathology_cohort_builder/USER_GUIDE_AND_SOP.md):** Standard Operating Procedure and guide for generating Arm Tables and Treatment Tables.
* 🛡️ **[Brand Guidelines &amp; Setup Docs](file:///c:/Users/somanath/farcast_db_production/docs_and_assets/):** Official Farcast Brand Identity Guidelines PDF, architecture resilience plans, and production setup guides.

---

## 🏗️ Repository Architecture Overview

```
farcast_db_production/
├── backend/                        # Python REST API Server & User Auth Database
├── frontend/                       # React + Vite Search Web UI Application
├── data/                           # Core Metadata Excel Datasets & Assay Tables
├── scripts/                        # Ingestion & Database Management Pipeline
├── docker/                         # PostgreSQL Docker Compose Setup
├── db_watcher/                     # Background File Auto-Watcher
├── histopathology_cohort_builder/  # Cohort Builder Executable & SOP Guide
├── cohort_data_files/              # Preserved Cohort Excel Datasets
├── docs_and_assets/                # Brand Identity & Documentation Archives
└── DATA_TRACKING_README.md         # Master Sample & Data Inventory Tracker
```

---

## 🚀 Quick Start Instructions

### 1. Launch Backend REST API Server

```bash
cd backend
python app.py
```

* API running on: `http://localhost:5052`

### 2. Launch Frontend UI Application

```bash
cd frontend
npm run dev
```

* UI running on: `http://localhost:5173`

---

## 🔒 User Authentication & Whitelist Administration

Admin users can manage whitelisted emails and accounts via the integrated **Admin Console** in the web application UI or using the backend command line tool:

```bash
python scripts/set_admin.py <user_email>
```
