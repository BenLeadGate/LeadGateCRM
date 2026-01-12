# Stop-Skript für den LeadGate Server
Write-Host "Stoppe LeadGate Server..." -ForegroundColor Yellow

# Finde und beende alle uvicorn-Prozesse
Get-Process | Where-Object {
    $_.ProcessName -eq "python" -and 
    $_.CommandLine -like "*uvicorn*backend.main:app*"
} | ForEach-Object {
    Write-Host "Stoppe Prozess ID: $($_.Id)" -ForegroundColor Red
    Stop-Process -Id $_.Id -Force
}

# Alternative: Beende alle Python-Prozesse (Vorsicht!)
$pythonProcesses = Get-Process python -ErrorAction SilentlyContinue
if ($pythonProcesses) {
    Write-Host "Gefundene Python-Prozesse:" -ForegroundColor Yellow
    $pythonProcesses | ForEach-Object {
        Write-Host "  PID: $($_.Id) - Start: $($_.StartTime)" -ForegroundColor Cyan
    }
    $confirm = Read-Host "Möchten Sie alle Python-Prozesse beenden? (j/n)"
    if ($confirm -eq "j" -or $confirm -eq "J") {
        $pythonProcesses | Stop-Process -Force
        Write-Host "Alle Python-Prozesse wurden beendet." -ForegroundColor Green
    }
} else {
    Write-Host "Keine Python-Prozesse gefunden." -ForegroundColor Green
}
