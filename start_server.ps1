# Start-Skript für den LeadGate Server
Write-Host "Starte LeadGate Server..." -ForegroundColor Green

# Wechsle ins Projektverzeichnis
Set-Location $PSScriptRoot

# Starte Server im Hintergrund
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$PSScriptRoot'; uvicorn backend.main:app --reload --host 0.0.0.0 --port 8004"

Write-Host "Server wird gestartet..." -ForegroundColor Yellow
Write-Host "Der Server läuft im Hintergrund in einem neuen PowerShell-Fenster." -ForegroundColor Cyan
Write-Host "Sie können dieses Fenster schließen." -ForegroundColor Cyan
Write-Host ""
Write-Host "Zum Stoppen des Servers: Schließen Sie das Server-Fenster oder verwenden Sie stop_server.ps1" -ForegroundColor Yellow
