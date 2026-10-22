# 🚀 FarCast DB — Standalone Office Server Synchronization Agent

This standalone package automatically synchronizes your office server files (`\\in-fs1\...`) directly into **Supabase Cloud Database** with:
- **Zero-Downtime Cache Invalidation** on the live web portal.
- **Arm Standard Naming Enforcement** (`ARM1`, `RXA`, etc.).
- **Automatic File-Lock Protection** (if Excel files are open by another user).
- **Email Notifications**: Weekly summary digests on success and instant crash alerts on failure.
- **Audit Logging**: Recorded in Supabase `audit_logs` table.

---

## 📁 Package Contents

```
farcast_sync_agent/
│
├── .env                     # Database, Network Paths, and Email Settings
├── .env.example             # Configuration template
├── requirements.txt         # Minimal Python dependencies
│
├── run_sync.bat             # 1-Click Manual Execution Script (Double-click to run)
├── setup_scheduler.bat      # 1-Click Windows Task Scheduler Installer (Weekly / Daily)
├── sync_all.py              # Master Synchronization Orchestrator
│
├── config.py                # Configuration loader & default UNC paths
├── logger.py                # Dual console + rotating file logger
├── email_notifier.py        # HTML email reporting & crash alerting
├── metadata_sync.py         # Registration Excel reader & atomic Supabase upsert
├── assay_sync.py            # Cytokine & Histopathology masterfile parser
├── nomenclature_resolver.py # Indication & Arm nomenclature overlay resolver
└── logs/                    # Execution logs (automatically created on first run)
```

---

## 📋 Prerequisites

1. **Python 3.10 or higher**:
   - Ensure Python is installed on the office machine and added to system PATH.
   - Verify by opening Command Prompt and typing:
     ```cmd
     python --version
     ```
2. **Access to Network Server (`\\in-fs1\...`)**:
   - The machine must be connected to the company network and able to access:
     `\\in-fs1\Farcast R&D\Farcast 2.0\`

---

## 🛠️ Step-by-Step Installation & Setup

### Step 1: Copy this Folder to Your Office Machine
You can place the `farcast_sync_agent` folder anywhere on your office machine or server (for example: `C:\Farcast\farcast_sync_agent`).

### Step 2: Install Required Python Packages
Open Command Prompt in this folder and run:
```cmd
pip install -r requirements.txt
```
*(Dependencies: `pandas`, `openpyxl`, `sqlalchemy`, `psycopg2-binary`, `python-dotenv`, `requests`)*

### Step 3: Configure Settings in `.env`
Open `.env` in Notepad. The database URL and network paths are already pre-configured.

If you wish to receive **Email Digests and Crash Alerts**, fill in your company SMTP details:
```env
SMTP_HOST=smtp.office365.com
SMTP_PORT=587
SMTP_USER=alerts@farcastbio.com
SMTP_PASSWORD=your_password
SMTP_FROM=alerts@farcastbio.com
NOTIFICATION_EMAILS=somanath@farcastbio.com
```

If you wish to automatically reload the live Railway portal cache upon each sync, add your Railway URL:
```env
RAILWAY_APP_URL=https://your-railway-app.up.railway.app
```

---

## 🏃 How to Run the Sync

### Option A: Manual Run (Anytime On-Demand)
Simply **double-click** [`run_sync.bat`](run_sync.bat), or run from Command Prompt:
```cmd
python sync_all.py
```
A terminal window will display the real-time progress of each step:
1. Synchronizing Clinical Metadata
2. Synchronizing Cytokines & Histopathology
3. Resolving Treatment Overlay
4. In-Memory Cache Invalidation
5. Recording Audit Log & Sending Email Digest

---

### Option B: Automated Scheduling (Weekly or Daily)
To set up automated background execution without manual intervention:

1. Right-click [`setup_scheduler.bat`](setup_scheduler.bat) and choose **"Run as administrator"**.
2. Select your preferred frequency:
   - **`[1]` Weekly**: Runs every Friday at 8:00 PM.
   - **`[2]` Daily**: Runs every night at 11:00 PM.
   - **`[3]` Hourly**: Runs every 1 hour.
3. Windows Task Scheduler will now run the sync automatically in the background.

---

## 📊 Viewing Logs and History

- Every execution generates a timestamped log file in the `logs/` directory:
  `logs/sync_YYYY-MM-DD_HH-MM-SS.log`
- The latest execution is always mirrored in:
  `logs/sync_latest.log`
- All executions are also recorded into the Supabase database table `audit_logs` under actor `system_office_cron`.
