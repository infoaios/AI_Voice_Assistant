@echo off
SETLOCAL ENABLEDELAYEDEXPANSION

REM ============================================================================
REM  Voice Platform - Cleanup Script (Windows)
REM ============================================================================
REM  Cleans up temporary files, cache, and optionally removes environments
REM  Usage: scripts\clean.bat
REM ============================================================================

set "SCRIPT_DIR=%~dp0"
set "PROJECT_ROOT=%SCRIPT_DIR%.."
cd /d "%PROJECT_ROOT%"

echo.
echo ============================================================================
echo   Voice Platform - Cleanup
echo ============================================================================
echo.

REM --- Clean Python cache ---
echo [INFO] Cleaning Python cache files...
FOR /D /R %%d IN (__pycache__) DO (
    IF EXIST "%%d" (
        echo   Removing: %%d
        RD /S /Q "%%d" 2>nul
    )
)
FOR /R %%f IN (*.pyc *.pyo *.pyd) DO (
    IF EXIST "%%f" (
        echo   Removing: %%f
        DEL /Q "%%f" 2>nul
    )
)
echo [OK] Python cache cleaned

REM --- Clean build artifacts ---
echo [INFO] Cleaning build artifacts...
IF EXIST "build" (
    RD /S /Q "build" 2>nul
    echo [OK] Removed build\ folder
)
IF EXIST "dist" (
    RD /S /Q "dist" 2>nul
    echo [OK] Removed dist\ folder
)
IF EXIST "*.egg-info" (
    FOR /D %%d IN (*.egg-info) DO (
        RD /S /Q "%%d" 2>nul
        echo [OK] Removed %%d
    )
)

REM --- Clean logs (optional) ---
SET /P CLEAN_LOGS="Clean log files? (y/n): "
IF /I "!CLEAN_LOGS!"=="y" (
    IF EXIST "logs" (
        DEL /Q "logs\*" 2>nul
        echo [OK] Log files cleaned
    )
)

REM --- Clean model cache (optional) ---
SET /P CLEAN_CACHE="Clean model cache (~/.cache/huggingface)? (y/n): "
IF /I "!CLEAN_CACHE!"=="y" (
    IF EXIST "%USERPROFILE%\.cache\huggingface" (
        SET /P CONFIRM="This will delete downloaded models. Continue? (y/n): "
        IF /I "!CONFIRM!"=="y" (
            RD /S /Q "%USERPROFILE%\.cache\huggingface" 2>nul
            echo [OK] Model cache cleaned
        )
    )
)

REM --- Remove environments (optional) ---
echo.
SET /P REMOVE_ENV="Remove conda environments? (y/n): "
IF /I "!REMOVE_ENV!"=="y" (
    where conda >nul 2>&1
    IF NOT ERRORLEVEL 1 (
        FOR /F "tokens=*" %%i IN ('conda env list ^| findstr "voice_assistant"') DO (
            SET LINE=%%i
            SET LINE=!LINE:*voice_assistant=voice_assistant!
            FOR /F "tokens=1" %%j IN ("!LINE!") DO (
                SET ENV_NAME=%%j
                SET /P CONFIRM="Remove environment !ENV_NAME!? (y/n): "
                IF /I "!CONFIRM!"=="y" (
                    call conda env remove -n !ENV_NAME! -y
                    IF NOT ERRORLEVEL 1 (
                        echo [OK] Removed environment: !ENV_NAME!
                    )
                )
            )
        )
    )
)

echo.
echo ============================================================================
echo   Cleanup Complete
echo ============================================================================
echo.

pause
ENDLOCAL

