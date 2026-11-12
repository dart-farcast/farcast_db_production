@echo off
REM ==============================================================================
REM FarCast DB v2 — Histopathology Data Ingestion Helper
REM Allows drag-and-drop or manual directory selection to ingest files into Supabase.
REM ==============================================================================
setlocal enabledelayedexpansion

title FarCast DB v2 — Histopathology Ingestion

echo ==============================================================================
echo             FarCast DB v2 - Histopathology Ingestion Tool
echo ==============================================================================
echo.

set "DEFAULT_DIR=%~dp0BP_shravan_curated_samples"

if "%~1"=="" (
    echo Enter the folder path containing the Excel masterfiles.
    echo (Press ENTER to use default: BP_shravan_curated_samples)
    set /p "TARGET_DIR=Folder path: "
    if "!TARGET_DIR!"=="" set "TARGET_DIR=%DEFAULT_DIR%"
) else (
    set "TARGET_DIR=%~1"
)

REM Remove surrounding quotes if entered
set "TARGET_DIR=%TARGET_DIR:"=%"

echo.
echo Target Directory: "%TARGET_DIR%"
echo.

if not exist "%TARGET_DIR%" (
    echo [ERROR] The directory "%TARGET_DIR%" does not exist.
    echo Please verify the path and try again.
    pause
    exit /b 1
)

echo Starting ingestion into Supabase Cloud PostgreSQL...
echo.

python "%~dp0scripts\ingest_histopathology.py" --dir "%TARGET_DIR%"

echo.
echo ==============================================================================
echo Execution finished. Press any key to exit.
echo ==============================================================================
pause
