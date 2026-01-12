# LeadGate CRM & Abrechnung

Ein lokal gehostetes MVP zur Verwaltung von Immobilienmaklern, Erfassung gelieferter Leads und automatischer monatlicher Abrechnung.

## Features

- **Makler-Verwaltung**: CRUD-Operationen für Immobilienmakler mit Vertragsdaten und Preiskonfiguration
- **Lead-Verwaltung**: Erfassung und Statusverwaltung von Leads (neu, geliefert, storniert)
- **Automatische Abrechnung**: Monatliche Rechnungserstellung basierend auf gelieferten Leads
- **Preislogik**: Automatische Unterscheidung zwischen Testphase (1. Monat) und Standardpreis
- **PDF-Generierung**: Automatische Erstellung von Rechnungen als PDF

## Tech Stack

- **Backend**: Python 3.11, FastAPI, SQLAlchemy, SQLite
- **Frontend**: HTML mit TailwindCSS (via CDN)
- **PDF**: WeasyPrint für HTML-zu-PDF-Konvertierung

## Installation

### Voraussetzungen

- Python 3.11 oder höher
- pip (Python Package Manager)

### Setup

1. **Repository klonen oder Projektordner öffnen**

2. **Virtuelle Umgebung erstellen (empfohlen)**:
   ```bash
   python -m venv venv
   ```

3. **Virtuelle Umgebung aktivieren**:
   - Windows:
     ```bash
     venv\Scripts\activate
     ```
   - Linux/Mac:
     ```bash
     source venv/bin/activate
     ```

4. **Dependencies installieren**:
   ```bash
   pip install -r requirements.txt
   ```

## Starten der Anwendung

```bash
uvicorn backend.main:app --reload
```

Die Anwendung läuft dann unter:
- Frontend: http://localhost:8000/
- API-Dokumentation: http://localhost:8000/docs
- Alternative API-Dokumentation: http://localhost:8000/redoc

## Verwendung

### 1. Makler anlegen

1. Navigiere zu "Makler" im Menü
2. Klicke auf "+ Neuer Makler"
3. Fülle die Formularfelder aus:
   - Firmenname (Pflichtfeld)
   - Ansprechpartner (optional)
   - Email (Pflichtfeld)
   - Adresse (optional)
   - Vertragsstart-Datum (Pflichtfeld)
   - Testphase Leads (Anzahl inkludierter Leads in Testphase)
   - Testphase Preis (Preis pro Lead im 1. Monat)
   - Standard Preis (Preis pro Lead ab dem 2. Monat)

### 2. Leads erfassen

1. Navigiere zu "Leads" im Menü
2. Klicke auf "+ Neuer Lead"
3. Wähle den Makler und den Status (neu, geliefert, storniert)
4. Speichere den Lead

**Hinweis**: Nur Leads mit Status "geliefert" werden für die Abrechnung berücksichtigt.

### 3. Monatsabrechnung erstellen

1. Navigiere zu "Abrechnung" im Menü
2. Klicke auf "+ Neue Monatsabrechnung"
3. Wähle Makler, Monat und Jahr
4. Die Rechnung wird automatisch erstellt basierend auf:
   - Anzahl gelieferter Leads im gewählten Monat
   - Vertragsmonat (1. Monat = Testphase-Preis, ab 2. Monat = Standard-Preis)

### 4. PDF-Rechnung herunterladen

1. In der Rechnungsübersicht klicke auf "PDF" bei der gewünschten Rechnung
2. Die PDF wird automatisch generiert und heruntergeladen

## Geschäftslogik

### Vertragsmonat-Berechnung

Der Vertragsmonat wird relativ zum Vertragsstart-Datum berechnet:
- Vertragsstart: 15.01.2025, Abrechnung: Januar 2025 → Vertragsmonat 1
- Vertragsstart: 15.01.2025, Abrechnung: Februar 2025 → Vertragsmonat 2

### Preislogik

- **Vertragsmonat 1**: Verwendung des `testphase_preis`
- **Vertragsmonat 2+**: Verwendung des `standard_preis`

### Abrechnung

- Es wird genau eine Rechnung pro Makler und Monat erstellt
- Bei erneutem Erstellen wird die vorhandene Rechnung zurückgegeben (idempotent)
- Nur Leads mit Status "geliefert" werden gezählt

## Projektstruktur

```
rechnungstool/
├── backend/
│   ├── main.py                 # FastAPI-App und Static-Files
│   ├── database.py             # Datenbank-Setup und Initialisierung
│   ├── schemas.py              # Pydantic-Schemas für API
│   ├── models/                 # SQLAlchemy-Modelle
│   │   ├── makler.py
│   │   ├── lead.py
│   │   └── rechnung.py
│   ├── routers/                # API-Router
│   │   ├── makler.py
│   │   ├── leads.py
│   │   └── rechnungen.py
│   └── services/               # Geschäftslogik
│       ├── abrechnung_service.py
│       └── pdf_service.py
├── frontend/
│   ├── index.html              # Übersichtsseite
│   ├── makler.html             # Makler-Verwaltung
│   ├── leads.html              # Lead-Verwaltung
│   └── abrechnung.html         # Abrechnung
├── requirements.txt            # Python-Dependencies
├── leadgate.db                 # SQLite-Datenbank (wird automatisch erstellt)
└── README.md                   # Diese Datei
```

## API-Endpunkte

### Makler
- `GET /api/makler/` - Liste aller Makler
- `GET /api/makler/{id}` - Einzelner Makler
- `POST /api/makler/` - Neuen Makler erstellen
- `PUT /api/makler/{id}` - Makler aktualisieren
- `DELETE /api/makler/{id}` - Makler löschen

### Leads
- `GET /api/leads/` - Liste aller Leads
- `GET /api/leads/{id}` - Einzelner Lead
- `POST /api/leads/` - Neuen Lead erstellen
- `PUT /api/leads/{id}` - Lead aktualisieren
- `DELETE /api/leads/{id}` - Lead löschen

### Rechnungen
- `GET /api/rechnungen/` - Liste aller Rechnungen
- `GET /api/rechnungen/{id}` - Einzelne Rechnung
- `GET /api/rechnungen/{id}/pdf` - PDF-Rechnung herunterladen
- `POST /api/rechnungen/monat/{makler_id}` - Monatsabrechnung erstellen

## Entwicklung

### Datenbank zurücksetzen

Lösche einfach die Datei `leadgate.db` im Projektverzeichnis. Beim nächsten Start wird die Datenbank automatisch neu erstellt.

### Weitere Entwicklung

- Frontend-Dateien befinden sich in `frontend/`
- Backend-Logik in `backend/`
- API-Dokumentation unter http://localhost:8000/docs

## Lizenz

Dieses Projekt ist ein MVP für lokale Nutzung.


