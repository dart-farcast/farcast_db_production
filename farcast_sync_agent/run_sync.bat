@echo off
:: ==============================================================================
:: FarCast DB — Manual Sync Trigger
:: Double-click this file to run an immediate sync against Supabase.
:: ==============================================================================
title FarCast DB Office Server Sync

cd /d "%~dp0"

echo ==============================================================================
echo   FARCAST BIOSCIENCES — MANUAL OFFICE SERVER SYNC RUNNER
echo ==============================================================================
echo.

where python >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Python was not found in your system PATH!
    echo Please install Python 3.10+ or ensure Python is added to PATH.
    echo.
    pause
    exit /b 1
)

echo Starting synchronization pipeline...
echo Log files will be stored in: %~dp0logs\
echo.

python sync_all.py

echo.
if %ERRORLEVEL% EQU 0 (
    echo ==============================================================================
    echo [SUCCESS] Synchronization finished with 0 errors!
    echo ==============================================================================
) else (
    echo ==============================================================================
    echo [ERROR] Synchronization encountered an issue. Check the logs above.
    echo ==============================================================================
)

echo.
pause
