@echo off
ECHO Starting Diabetes Management Platform...
ECHO.

REM --- Start Backend ---
ECHO Starting Backend Server...
ECHO Make sure your MongoDB server is running.
START "Diabetes Backend" cmd /k "cd /D diabetes_backend && call .\venv\Scripts\activate.bat && python app.py"
ECHO Backend server starting in a new window...
ECHO.

REM --- Start Frontend ---
ECHO Starting Frontend Dev Server...
REM The 'npm install' command can be commented out if dependencies are already installed by adding REM at the start of the line.
START "Diabetes Frontend" cmd /k "cd /D diabetes_frontend && npm install && npm run dev"
ECHO Frontend dev server starting in a new window...
ECHO.

REM --- Start Patient PWA ---
ECHO Starting Patient PWA Dev Server...
REM The 'npm install' command can be commented out if dependencies are already installed by adding REM at the start of the line.
START "Diabetes Patient PWA" cmd /k "cd /D diabetes_patient_pwa && npm install && npm run dev"
ECHO Patient PWA dev server starting in a new window...
ECHO.

ECHO All services are attempting to start in separate windows.
ECHO Please check each window for logs and status.
