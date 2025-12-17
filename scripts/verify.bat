@echo off
SETLOCAL ENABLEDELAYEDEXPANSION

REM ============================================================================
REM  Voice Platform - Environment Verification (Windows)
REM ============================================================================
REM  Verifies that the environment is set up correctly
REM  Usage: scripts\verify.bat
REM ============================================================================

set "SCRIPT_DIR=%~dp0"
set "PROJECT_ROOT=%SCRIPT_DIR%.."
cd /d "%PROJECT_ROOT%"

echo.
echo ============================================================================
echo   Voice Platform - Environment Verification
echo ============================================================================
echo.

REM --- Check conda ---
where conda >nul 2>&1
IF ERRORLEVEL 1 (
    echo [ERROR] Conda not found.
    EXIT /B 1
)

REM --- Find environment ---
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
    echo Please run: scripts\setup.bat
    pause
    EXIT /B 1
)

echo [INFO] Verifying environment: !ENV_NAME!
echo.

REM --- Activate environment ---
call conda activate !ENV_NAME!
IF ERRORLEVEL 1 (
    echo [ERROR] Failed to activate environment.
    pause
    EXIT /B 1
)

REM --- Verify packages ---
echo [INFO] Checking critical packages...
echo.

SET ERRORS=0

python -c "import torch; print('PyTorch:', torch.__version__); print('CUDA available:', torch.cuda.is_available())" 2>nul
IF ERRORLEVEL 1 (
    echo [ERROR] PyTorch not installed or not working
    SET /A ERRORS+=1
) ELSE (
    echo [OK] PyTorch installed
)

python -c "import transformers; print('Transformers:', transformers.__version__)" 2>nul
IF ERRORLEVEL 1 (
    echo [ERROR] Transformers not installed
    SET /A ERRORS+=1
) ELSE (
    echo [OK] Transformers installed
)

python -c "from faster_whisper import WhisperModel; print('Faster Whisper: OK')" 2>nul
IF ERRORLEVEL 1 (
    echo [ERROR] Faster Whisper not installed
    SET /A ERRORS+=1
) ELSE (
    echo [OK] Faster Whisper installed
)

python -c "from TTS.api import TTS; print('Coqui TTS: OK')" 2>nul
IF ERRORLEVEL 1 (
    echo [ERROR] Coqui TTS not installed
    SET /A ERRORS+=1
) ELSE (
    echo [OK] Coqui TTS installed
)

python -c "import sounddevice; import soundfile; print('Audio libraries: OK')" 2>nul
IF ERRORLEVEL 1 (
    echo [ERROR] Audio libraries not installed
    SET /A ERRORS+=1
) ELSE (
    echo [OK] Audio libraries installed
)

python -c "import fastapi; print('FastAPI:', fastapi.__version__)" 2>nul
IF ERRORLEVEL 1 (
    echo [ERROR] FastAPI not installed
    SET /A ERRORS+=1
) ELSE (
    echo [OK] FastAPI installed
)

python -c "import pydantic; print('Pydantic:', pydantic.__version__)" 2>nul
IF ERRORLEVEL 1 (
    echo [ERROR] Pydantic not installed
    SET /A ERRORS+=1
) ELSE (
    echo [OK] Pydantic installed
)

REM --- Check files ---
echo.
echo [INFO] Checking required files...

IF EXIST "%PROJECT_ROOT%\data\restaurant_data.json" (
    echo [OK] restaurant_data.json found
) ELSE (
    echo [WARN] restaurant_data.json not found (required for application)
    SET /A ERRORS+=1
)

IF EXIST "%PROJECT_ROOT%\data\saved_voices\refe2.wav" (
    echo [OK] Voice clone file found
) ELSE (
    echo [WARN] Voice clone file not found (application may use default voice)
)

REM --- Summary ---
echo.
echo ============================================================================
IF !ERRORS! EQU 0 (
    echo   Verification Complete - All checks passed!
    echo ============================================================================
    echo.
    echo Environment is ready to use.
    echo Run application with: scripts\run.bat
) ELSE (
    echo   Verification Complete - %ERRORS% error(s) found
    echo ============================================================================
    echo.
    echo Please fix the errors above before running the application.
    echo.
)
echo.

pause
ENDLOCAL

