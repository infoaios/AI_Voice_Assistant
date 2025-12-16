@echo off
SETLOCAL ENABLEDELAYEDEXPANSION

REM ============================================================================
REM  Voice Platform - Environment Setup Script (Windows)
REM ============================================================================
REM  Automatically detects hardware and sets up the appropriate conda environment
REM  Usage: scripts\setup.bat
REM ============================================================================

set "SCRIPT_DIR=%~dp0"
set "PROJECT_ROOT=%SCRIPT_DIR%.."
cd /d "%PROJECT_ROOT%"

echo.
echo ============================================================================
echo   Voice Platform - Environment Setup
echo ============================================================================
echo.

REM --- Check conda ---
where conda >nul 2>&1
IF ERRORLEVEL 1 (
    echo [ERROR] Conda not found in PATH.
    echo.
    echo Please install Anaconda or Miniconda, or open "Anaconda Prompt".
    echo Download: https://www.anaconda.com/products/distribution
    echo.
    pause
    EXIT /B 1
)

echo [OK] Conda found.

REM --- Detect GPU ---
echo.
echo [INFO] Detecting hardware configuration...
nvidia-smi >nul 2>&1
IF ERRORLEVEL 1 (
    echo [INFO] No GPU detected. Using CPU environment.
    SET ENV_TYPE=cpu
    SET ENV_FILE=cpu_env.yml
    SET ENV_NAME=voice_assistant_cpu
    GOTO :CHECK_ENV
)

REM Get GPU name
SET GPU_NAME=
FOR /F "skip=1 tokens=*" %%i IN ('nvidia-smi --query-gpu^=name --format^=csv 2^>nul') DO (
    SET GPU_NAME=%%i
    GOTO :PROCESS_GPU
)

:PROCESS_GPU
SET GPU_NAME=!GPU_NAME:"=!

IF "!GPU_NAME!"=="" (
    echo [WARN] GPU detected but could not determine model.
    SET ENV_TYPE=gpu3080
    SET ENV_FILE=gpu3080_env.yml
    SET ENV_NAME=voice_assistant_gpu3080
    GOTO :CHECK_ENV
)

echo [INFO] GPU detected: !GPU_NAME!

REM Check GPU model
echo !GPU_NAME! | findstr /i "3050" >nul
IF NOT ERRORLEVEL 1 (
    SET ENV_TYPE=gpu3050
    SET ENV_FILE=gpu3050_env.yml
    SET ENV_NAME=voice_assistant_gpu3050
    GOTO :CHECK_ENV
)

echo !GPU_NAME! | findstr /i "3080" >nul
IF NOT ERRORLEVEL 1 (
    SET ENV_TYPE=gpu3080
    SET ENV_FILE=gpu3080_env.yml
    SET ENV_NAME=voice_assistant_gpu3080
    GOTO :CHECK_ENV
)

echo !GPU_NAME! | findstr /i "5080" >nul
IF NOT ERRORLEVEL 1 (
    SET ENV_TYPE=gpu5080
    SET ENV_FILE=gpu5080_env.yml
    SET ENV_NAME=voice_assistant_gpu5080
    GOTO :CHECK_ENV
)

REM Default to RTX 3080 for unknown GPUs
echo [WARN] Unknown GPU model: !GPU_NAME!
echo [INFO] Using RTX 3080 configuration (CUDA 11.8 compatible).
SET ENV_TYPE=gpu3080
SET ENV_FILE=gpu3080_env.yml
SET ENV_NAME=voice_assistant_gpu3080

:CHECK_ENV
echo.
echo ============================================================================
echo   Environment: %ENV_NAME%
echo ============================================================================
echo.

REM Check if environment exists
call conda env list | findstr /C:"%ENV_NAME%" >nul
IF NOT ERRORLEVEL 1 (
    echo [OK] Environment "%ENV_NAME%" already exists.
    SET /P UPDATE_ENV="Update existing environment? (y/n): "
    IF /I NOT "!UPDATE_ENV!"=="y" (
        echo [INFO] Skipping environment setup.
        GOTO :SUCCESS
    )
    echo.
    echo [INFO] Updating environment...
    SET ENV_FILE_PATH=%PROJECT_ROOT%\env\%ENV_FILE%
    call conda env update -f "%ENV_FILE_PATH%" --prune
    IF ERRORLEVEL 1 (
        echo [ERROR] Failed to update environment.
        pause
        EXIT /B 1
    )
    echo [SUCCESS] Environment updated!
    GOTO :SUCCESS
)

REM Create new environment
SET ENV_FILE_PATH=%PROJECT_ROOT%\env\%ENV_FILE%

IF NOT EXIST "%ENV_FILE_PATH%" (
    echo [ERROR] Environment file not found: %ENV_FILE_PATH%
    pause
    EXIT /B 1
)

echo [INFO] Creating environment (this may take 10-20 minutes)...
echo [INFO] File: %ENV_FILE%
echo.

call conda env create -f "%ENV_FILE_PATH%"
IF ERRORLEVEL 1 (
    echo.
    echo [ERROR] Failed to create environment.
    echo.
    echo Troubleshooting:
    echo   1. Check conda installation: conda --version
    echo   2. Try using mamba (faster): mamba env create -f "%ENV_FILE_PATH%"
    echo   3. Check disk space (requires ~5GB)
    echo   4. Check internet connection
    echo.
    pause
    EXIT /B 1
)

:SUCCESS
echo.
echo ============================================================================
echo   Setup Complete!
echo ============================================================================
echo.
echo Next steps:
echo   1. Activate environment: conda activate %ENV_NAME%
echo   2. Verify installation: scripts\verify.bat
echo   3. Run application: scripts\run.bat
echo.
pause
ENDLOCAL

