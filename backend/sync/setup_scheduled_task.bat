@echo off
:: ==============================================================================
:: FarCast DB v2 — Windows Task Scheduler Registration Script
:: Registers the Automated Office Server Sync Pipeline as a Windows Scheduled Task
:: ==============================================================================

set TASK_NAME=FarcastDB_OfficeServer_Sync
set PYTHON_EXE=python
set SCRIPT_DIR=%~dp0
set SCRIPT_PATH=%SCRIPT_DIR%sync_all.py
set WORKING_DIR=%SCRIPT_DIR%..\..

echo ==============================================================================
echo   FarCast DB v2 — Windows Task Scheduler Setup
echo ==============================================================================
echo Task Name   : %TASK_NAME%
echo Script Path : %SCRIPT_PATH%
echo.

echo Choose execution schedule:
echo   [1] Weekly (Every Friday at 8:00 PM)
echo   [2] Daily  (Every day at 11:00 PM)
echo   [3] Cancel
set /p SCHEDULE_CHOICE="Enter choice [1, 2, or 3]: "

if "%SCHEDULE_CHOICE%"=="1" (
    echo Registering Weekly Scheduled Task (Fridays at 20:00)...
    schtasks /create /tn "%TASK_NAME%" /tr "%PYTHON_EXE% \"%SCRIPT_PATH%\"" /sc WEEKLY /d FRI /st 20:00 /ru "%USERNAME%" /f
) else if "%SCHEDULE_CHOICE%"=="2" (
    echo Registering Daily Scheduled Task (Daily at 23:00)...
    schtasks /create /tn "%TASK_NAME%" /tr "%PYTHON_EXE% \"%SCRIPT_PATH%\"" /sc DAILY /st 23:00 /ru "%USERNAME%" /f
) else (
    echo Setup cancelled.
    exit /b 0
)

if %ERRORLEVEL% EQU 0 (
    echo.
    echo [SUCCESS] Scheduled Task "%TASK_NAME%" registered successfully!
    echo To run it immediately on demand, run:
    echo   schtasks /run /tn "%TASK_NAME%"
) else (
    echo.
    echo [ERROR] Failed to register task. Please run this Command Prompt as Administrator.
)

pause
