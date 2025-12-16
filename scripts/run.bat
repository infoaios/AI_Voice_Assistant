@echo off
SETLOCAL ENABLEDELAYEDEXPANSION

REM ============================================================================
REM  Voice Platform - Run Application (Windows)
REM ============================================================================
REM  Automatically detects environment and runs the application
REM  Usage: scripts\run.bat
REM ============================================================================

set "SCRIPT_DIR=%~dp0"
set "PROJECT_ROOT=%SCRIPT_DIR%.."
cd /d "%PROJECT_ROOT%"

echo.
echo ============================================================================
echo   Voice Platform - Starting Application
echo ============================================================================
echo.

REM --- Check conda ---
where conda >nul 2>&1
IF ERRORLEVEL 1 (
    echo [ERROR] Conda not found. Please install Anaconda or Miniconda.
    pause
    EXIT /B 1
)

REM --- Detect environment ---
echo [INFO] Detecting environment...

REM Try to find existing environment
SET ENV_NAME=
FOR /F "tokens=*" %%i IN ('conda env list ^| findstr "voice_assistant"') DO (
    SET LINE=%%i
    SET LINE=!LINE:*voice_assistant=voice_assistant!
    FOR /F "tokens=1" %%j IN ("!LINE!") DO SET ENV_NAME=%%j
    GOTO :FOUND_ENV
)

:FOUND_ENV
IF "!ENV_NAME!"=="" (
    echo [ERROR] No voice_assistant environment found.
    echo.
    echo Please run setup first: scripts\setup.bat
    pause
    EXIT /B 1
)

echo [OK] Found environment: !ENV_NAME!

REM --- Activate and run ---
echo.
echo [INFO] Activating environment...
call conda activate !ENV_NAME!
IF ERRORLEVEL 1 (
    echo [ERROR] Failed to activate environment.
    pause
    EXIT /B 1
)

REM --- Check required files ---
IF NOT EXIST "%PROJECT_ROOT%\data\restaurant_data.json" (
    echo [WARN] restaurant_data.json not found in data\ folder
    echo [INFO] Application may not work correctly without this file.
    echo.
)

REM --- Run application ---
echo.
echo [INFO] Starting application...
echo [INFO] Press Ctrl+C to stop
echo.

cd /d "%PROJECT_ROOT%\voice_platform"
python main.py

IF ERRORLEVEL 1 (
    echo.
    echo [ERROR] Application failed to run.
    echo.
    echo Troubleshooting:
    echo   1. Verify environment: scripts\verify.bat
    echo   2. Check logs: logs\assistant.log
    echo   3. Ensure data\restaurant_data.json exists
    echo.
    pause
    EXIT /B 1
)

ENDLOCAL

