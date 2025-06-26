@echo off
ECHO Installing Diabetes Management Platform dependencies...
ECHO.

REM --- Backend Setup ---
ECHO Setting up Python virtual environment...
IF NOT EXIST diabetes_backend\venv (
    python -m venv diabetes_backend\venv
)

ECHO Activating environment and installing Python packages...
call diabetes_backend\venv\Scripts\activate.bat && pip install -r diabetes_backend\requirements.txt && deactivate
ECHO Backend dependencies installed.
ECHO.

REM --- Frontend Setup ---
ECHO Installing Doctor Portal packages...
cd /D diabetes_frontend
call npm install
cd ..

ECHO Installing Patient PWA packages...
cd /D diabetes_patient_pwa
call npm install
cd ..

ECHO Installation complete. Configure your .env files before running the platform.
