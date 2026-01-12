#!/bin/bash
# LeadGate CRM - Produktions-Startskript
# Verwendung: ./start_production.sh

set -e  # Beende bei Fehlern

echo "🚀 Starte LeadGate CRM in Produktion..."

# Prüfe ob .env existiert
if [ ! -f .env ]; then
    echo "❌ FEHLER: .env Datei nicht gefunden!"
    echo "   Kopiere env.production.example zu .env und konfiguriere alle Werte."
    exit 1
fi

# Prüfe ob JWT_SECRET_KEY gesetzt ist
if grep -q "your-secret-key-change-this-in-production" .env || grep -q "^JWT_SECRET_KEY=$" .env; then
    echo "⚠️  WARNUNG: JWT_SECRET_KEY nicht gesetzt!"
    echo "   Setze einen sicheren Secret Key in der .env-Datei."
    read -p "   Trotzdem fortfahren? (j/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Jj]$ ]]; then
        exit 1
    fi
fi

# Prüfe ob Environment auf production gesetzt ist
if ! grep -q "ENVIRONMENT=production" .env; then
    echo "⚠️  WARNUNG: ENVIRONMENT nicht auf 'production' gesetzt!"
    read -p "   Trotzdem fortfahren? (j/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Jj]$ ]]; then
        exit 1
    fi
fi

# Aktiviere virtuelle Umgebung falls vorhanden
if [ -d "venv" ]; then
    echo "📦 Aktiviere virtuelle Umgebung..."
    source venv/bin/activate
fi

# Prüfe Dependencies
echo "🔍 Prüfe Dependencies..."
if ! python -c "import fastapi, uvicorn, sqlalchemy" 2>/dev/null; then
    echo "❌ FEHLER: Dependencies nicht installiert!"
    echo "   Führe aus: pip install -r requirements.txt"
    exit 1
fi

# Erstelle notwendige Verzeichnisse
echo "📁 Erstelle Verzeichnisse..."
mkdir -p logs
mkdir -p uploads
mkdir -p makler_dokumente
mkdir -p backups

# Starte Server
echo "🌟 Starte Server..."
echo "   Host: 0.0.0.0"
echo "   Port: 8004"
echo "   Workers: 4"
echo "   Environment: production"
echo ""

# Starte mit mehreren Workers für Produktion
exec uvicorn backend.main:app \
    --host 0.0.0.0 \
    --port 8004 \
    --workers 4 \
    --log-level info \
    --no-access-log \
    --proxy-headers \
    --forwarded-allow-ips "*"

