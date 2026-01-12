# LeadGate CRM - Produktions-Startskript (PowerShell)
# Verwendung: .\start_production.ps1

Write-Host "🚀 Starte LeadGate CRM in Produktion..." -ForegroundColor Green

# Prüfe ob .env existiert
if (-not (Test-Path .env)) {
    Write-Host "❌ FEHLER: .env Datei nicht gefunden!" -ForegroundColor Red
    Write-Host "   Kopiere env.production.example zu .env und konfiguriere alle Werte." -ForegroundColor Yellow
    exit 1
}

# Prüfe ob JWT_SECRET_KEY gesetzt ist
$envContent = Get-Content .env -Raw
if ($envContent -match "your-secret-key-change-this-in-production" -or $envContent -match "^JWT_SECRET_KEY=$") {
    Write-Host "⚠️  WARNUNG: JWT_SECRET_KEY nicht gesetzt!" -ForegroundColor Yellow
    Write-Host "   Setze einen sicheren Secret Key in der .env-Datei." -ForegroundColor Yellow
    $response = Read-Host "   Trotzdem fortfahren? (j/N)"
    if ($response -ne "j" -and $response -ne "J") {
        exit 1
    }
}

# Prüfe ob Environment auf production gesetzt ist
if (-not ($envContent -match "ENVIRONMENT=production")) {
    Write-Host "⚠️  WARNUNG: ENVIRONMENT nicht auf 'production' gesetzt!" -ForegroundColor Yellow
    $response = Read-Host "   Trotzdem fortfahren? (j/N)"
    if ($response -ne "j" -and $response -ne "J") {
        exit 1
    }
}

# Aktiviere virtuelle Umgebung falls vorhanden
if (Test-Path "venv\Scripts\Activate.ps1") {
    Write-Host "📦 Aktiviere virtuelle Umgebung..." -ForegroundColor Cyan
    & "venv\Scripts\Activate.ps1"
}

# Prüfe Dependencies
Write-Host "🔍 Prüfe Dependencies..." -ForegroundColor Cyan
try {
    python -c "import fastapi, uvicorn, sqlalchemy" 2>$null
    if ($LASTEXITCODE -ne 0) {
        throw "Dependencies fehlen"
    }
} catch {
    Write-Host "❌ FEHLER: Dependencies nicht installiert!" -ForegroundColor Red
    Write-Host "   Führe aus: pip install -r requirements.txt" -ForegroundColor Yellow
    exit 1
}

# Erstelle notwendige Verzeichnisse
Write-Host "📁 Erstelle Verzeichnisse..." -ForegroundColor Cyan
@("logs", "uploads", "makler_dokumente", "backups") | ForEach-Object {
    if (-not (Test-Path $_)) {
        New-Item -ItemType Directory -Path $_ | Out-Null
    }
}

# Starte Server
Write-Host "🌟 Starte Server..." -ForegroundColor Green
Write-Host "   Host: 0.0.0.0" -ForegroundColor Cyan
Write-Host "   Port: 8004" -ForegroundColor Cyan
Write-Host "   Workers: 4" -ForegroundColor Cyan
Write-Host "   Environment: production" -ForegroundColor Cyan
Write-Host ""

# Starte mit mehreren Workers für Produktion
uvicorn backend.main:app `
    --host 0.0.0.0 `
    --port 8004 `
    --workers 4 `
    --log-level info `
    --no-access-log `
    --proxy-headers `
    --forwarded-allow-ips "*"

