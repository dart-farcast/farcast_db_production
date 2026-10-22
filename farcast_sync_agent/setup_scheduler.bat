@echo off
:: ==============================================================================
:: FarCast DB — Windows Task Scheduler Setup
:: Registers or manages the automated background sync task.
:: ==============================================================================
title FarCast DB Windows Task Scheduler Setup

cd /d "%~dp0"

set TASK_NAME=FarcastDB_OfficeServer_Sync
set SCRIPT_PATH=%~dp0sync_all.py
set PYTHON_EXE=python

echo ==============================================================================
echo   FARCAST BIOSCIENCES — WINDOWS TASK SCHEDULER SETUP
echo ==============================================================================
echo Task Name   : %TASK_NAME%
echo Script Path : %SCRIPT_PATH%
echo.

echo Choose an action:
echo   [1] Register Weekly Task (Every Friday at 8:00 PM)
echo   [2] Register Daily Task  (Every day at 11:00 PM)
echo   [3] Register Hourly Task (Runs every 1 hour)
echo   [4] Run the Scheduled Task NOW
echo   [5] Check Scheduled Task Status
echo   [6] Remove / Delete the Scheduled Task
echo   [7] Exit
echo.
set /p CHOICE="Enter choice [1-7]: "

if "%CHOICE%"=="1" goto REGISTER_WEEKLY
if "%CHOICE%"=="2" goto REGISTER_DAILY
if "%CHOICE%"=="3" goto REGISTER_HOURLY
if "%CHOICE%"=="4" goto RUN_NOW
if "%CHOICE%"=="5" goto CHECK_STATUS
if "%CHOICE%"=="6" goto REMOVE_TASK
if "%CHOICE%"=="7" goto END
goto END

:REGISTER_WEEKLY
echo.
echo Registering Weekly task (Fridays at 20:00)...
schtasks /create /tn "%TASK_NAME%" /tr "%PYTHON_EXE% \"%SCRIPT_PATH%\"" /sc WEEKLY /d FRI /st 20:00 /ru "%USERNAME%" /f
goto FINISH

:REGISTER_DAILY
echo.
echo Registering Daily task (Daily at 23:00)...
schtasks /create /tn "%TASK_NAME%" /tr "%PYTHON_EXE% \"%SCRIPT_PATH%\"" /sc DAILY /st 23:00 /ru "%USERNAME%" /f
goto FINISH

:REGISTER_HOURLY
echo.
echo Registering Hourly task (Every 1 hour)...
schtasks /create /tn "%TASK_NAME%" /tr "%PYTHON_EXE% \"%SCRIPT_PATH%\"" /sc HOURLY /mo 1 /ru "%USERNAME%" /f
goto FINISH

:RUN_NOW
echo.
echo Triggering "%TASK_NAME%" now in background...
schtasks /run /tn "%TASK_NAME%"
goto FINISH

:CHECK_STATUS
echo.
schtasks /query /tn "%TASK_NAME%" /fo LIST /v
goto FINISH

:REMOVE_TASK
echo.
echo Removing "%TASK_NAME%"...
schtasks /delete /tn "%TASK_NAME%" /f
goto FINISH

:FINISH
echo.
if %ERRORLEVEL% EQU 0 (
    echo [SUCCESS] Operation completed successfully!
) else (
    echo [NOTICE] If permission was denied, please right-click this .bat file and select 'Run as administrator'.
)

:END
echo.
pause
