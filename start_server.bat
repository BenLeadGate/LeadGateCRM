@echo off
echo Starte LeadGate Server...
cd /d %~dp0
start "LeadGate Server" cmd /k "uvicorn backend.main:app --reload --host 0.0.0.0 --port 8004"
echo.
echo Server wird in einem neuen Fenster gestartet...
echo Sie können dieses Fenster schließen.
echo.
pause
