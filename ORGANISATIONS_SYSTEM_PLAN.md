# Organisations- und Koordinationssystem für LeadGate

## Ziel
Ein zentrales Dashboard/System, das Telefonisten zeigt:
- **Für welche Makler sie qualifizieren sollen**
- **Wie viele Leads jeder Makler noch benötigt**
- **Priorisierung und Verfügbarkeit**

## Aktuelle Situation

### Zwei Rechnungssysteme:
1. **Altes System** (`rechnungssystem_typ = "alt"`):
   - Monatliche Rechnungen
   - Feste Soll-Lead-Anzahl möglich (`monatliche_soll_leads`)
   - Testphase-Leads im ersten Monat (`testphase_leads`)

2. **Neues System** (`rechnungssystem_typ = "neu"`):
   - Prepaid-Credits
   - **KEINE feste Anzahl** - alles wird dynamisch koordiniert
   - Credits-Stand bestimmt, wie viele Leads möglich sind

### Aktuelle Datenstruktur:
- `monatliche_soll_leads`: Feste Anzahl (nur für altes System relevant)
- `testphase_leads`: Anzahl im ersten Monat
- `rechnungssystem_typ`: "alt" oder "neu"
- Credits-Stand: Für neues System

## Anforderungen

### 1. Dashboard für Telefonisten
**Ziel:** Übersicht, welche Makler noch Leads benötigen

**Anzeige pro Makler:**
- Makler-Info (Name, Gebiet)
- **Aktueller Status:**
  - Altes System: `Soll: X | Ist: Y | Fehlend: Z`
  - Neues System: `Credits: X€ | Verfügbar: ~Y Leads | Status`
- **Priorität/Verfügbarkeit:**
  - ✅ Kann Leads bekommen
  - ⚠️ Wenig Credits / Fast voll
  - ❌ Keine Leads mehr möglich
- **Gebiet/PLZ:** Welche PLZ der Makler abdeckt

### 2. Berechnungslogik

#### Für Altes System:
```
Soll-Leads = monatliche_soll_leads ODER testphase_leads (nur Monat 1)
Ist-Leads = Anzahl qualifizierter Leads im aktuellen Monat
Fehlend = Soll - Ist (wenn Soll > Ist)
Status = "Kann Leads bekommen" wenn Fehlend > 0
```

#### Für Neues System (Credits):
```
Credits-Stand = Summe aller Credits-Transaktionen
Durchschnittlicher Preis = Berechne basierend auf Vertragsmonat und bisherigen Leads
Verfügbare Leads = Credits-Stand / Durchschnittlicher Preis
Status = 
  - "Kann Leads bekommen" wenn Credits > nächster Lead-Preis
  - "Wenig Credits" wenn Credits < 2x nächster Lead-Preis
  - "Keine Credits" wenn Credits < nächster Lead-Preis
```

### 3. Priorisierung

**Sortierung:**
1. **Höchste Priorität:** Makler mit wenig Credits (warnung)
2. **Hohe Priorität:** Makler mit fehlenden Leads (altes System)
3. **Normale Priorität:** Makler mit Credits (neues System)
4. **Niedrige Priorität:** Makler die bereits voll sind

### 4. Filter & Suche

**Filter:**
- Nach Gebiet/PLZ
- Nach Rechnungssystem (alt/neu)
- Nach Status (kann Leads / wenig Credits / voll)
- Nach Priorität

**Suche:**
- Nach Makler-Name
- Nach PLZ

### 5. Detailansicht pro Makler

**Zeigt:**
- Aktuelle Leads im Monat
- Credits-Stand (wenn neues System)
- Soll/Ist (wenn altes System)
- Durchschnittlicher Preis pro Lead
- Verfügbare Leads (geschätzt)
- Letzte Lead-Qualifizierung
- Gebiet/PLZ

## Technische Umsetzung

### Backend-Endpunkte

#### 1. `/api/telefonist/dashboard` oder `/api/organisation/dashboard`
**Zweck:** Übersicht für Telefonisten

**Response:**
```json
{
  "makler_liste": [
    {
      "makler_id": 1,
      "firmenname": "Beispiel Makler",
      "gebiet": "10115, 10117",
      "rechnungssystem_typ": "neu",
      "status": "kann_leads",
      "prioritaet": "hoch",
      "credits_stand": 500.0,
      "durchschnittlicher_preis": 75.0,
      "verfuegbare_leads": 6,
      "ist_leads_dieser_monat": 2,
      "soll_leads": null,
      "fehlend_leads": null,
      "warnung": "Wenig Credits"
    },
    {
      "makler_id": 2,
      "firmenname": "Alter Makler",
      "gebiet": "10119",
      "rechnungssystem_typ": "alt",
      "status": "kann_leads",
      "prioritaet": "normal",
      "credits_stand": null,
      "durchschnittlicher_preis": 100.0,
      "verfuegbare_leads": null,
      "ist_leads_dieser_monat": 5,
      "soll_leads": 10,
      "fehlend_leads": 5,
      "warnung": null
    }
  ],
  "statistiken": {
    "gesamt_makler": 10,
    "kann_leads": 7,
    "wenig_credits": 2,
    "voll": 1
  }
}
```

#### 2. `/api/telefonist/makler/{makler_id}/verfuegbarkeit`
**Zweck:** Detaillierte Verfügbarkeit für einen Makler

**Response:**
```json
{
  "makler_id": 1,
  "firmenname": "Beispiel Makler",
  "rechnungssystem_typ": "neu",
  "credits_stand": 500.0,
  "durchschnittlicher_preis": 75.0,
  "verfuegbare_leads": 6,
  "naechster_lead_preis": 75.0,
  "ist_leads_dieser_monat": 2,
  "soll_leads": null,
  "fehlend_leads": null,
  "status": "kann_leads",
  "warnung": null,
  "gebiet": ["10115", "10117"]
}
```

### Frontend-Seite

#### Neue Seite: `telefonist_dashboard.html` oder `organisation.html`

**Layout:**
- **Header:** "Lead-Koordination" oder "Organisation"
- **Filter-Bar:** 
  - Dropdown: Alle / Kann Leads / Wenig Credits / Voll
  - Dropdown: Alle Systeme / Altes System / Neues System
  - Suchfeld: Nach Makler oder PLZ
- **Makler-Karten:**
  - Kompakt: Name, Status, Verfügbarkeit
  - Farbe: Grün (kann Leads), Gelb (wenig Credits), Rot (voll)
  - Badge: Priorität
  - Klick: Öffnet Detailansicht

**Detailansicht (Modal oder Sidebar):**
- Vollständige Informationen
- Credits-Verlauf (Graph)
- Lead-Historie
- Gebiet/PLZ-Übersicht

## Berechnungslogik (Backend)

### Service: `organisation_service.py`

#### Funktionen:

1. **`berechne_makler_verfuegbarkeit(db, makler, monat, jahr)`**
   - Berechnet für einen Makler:
     - Status (kann_leads, wenig_credits, voll)
     - Verfügbare Leads (für Credits-System)
     - Fehlend (für altes System)
     - Priorität

2. **`berechne_durchschnittlichen_preis(db, makler, monat, jahr)`**
   - Berechnet durchschnittlichen Preis basierend auf:
     - Vertragsmonat
     - Bisherige Leads im Monat
     - Preislogik (erste X Leads, danach, Standard)

3. **`berechne_verfuegbare_leads_aus_credits(db, makler)`**
   - Credits-Stand / Durchschnittlicher Preis
   - Berücksichtigt Preislogik

4. **`get_telefonist_dashboard(db, filter_status=None, filter_system=None, suche=None)`**
   - Hauptfunktion für Dashboard
   - Filtert und sortiert Makler
   - Gibt Liste zurück

## UI/UX Design

### Dashboard-Karten

**Kompakt-Ansicht:**
```
┌─────────────────────────────────────┐
│ 🟢 Beispiel Makler GmbH            │
│ Gebiet: 10115, 10117               │
│ Credits: 500€ | ~6 Leads verfügbar │
│ Status: Kann Leads bekommen         │
│ [Details] [Leads zuweisen]         │
└─────────────────────────────────────┘
```

**Erweitert:**
```
┌─────────────────────────────────────┐
│ 🟡 Anderer Makler                   │
│ Gebiet: 10119                       │
│ Soll: 10 | Ist: 5 | Fehlend: 5     │
│ Status: ⚠️ Wenig Credits            │
│ [Details] [Leads zuweisen]         │
└─────────────────────────────────────┘
```

### Farbcodierung:
- 🟢 **Grün:** Kann Leads bekommen (genug Credits / noch Platz)
- 🟡 **Gelb:** Wenig Credits / Fast voll (Warnung)
- 🔴 **Rot:** Keine Leads mehr möglich (keine Credits / voll)

### Priorität-Badges:
- 🔥 **Hoch:** Wenig Credits oder viele fehlende Leads
- ⚡ **Mittel:** Normale Priorität
- 📋 **Niedrig:** Bereits gut versorgt

## Offene Fragen / Entscheidungen

1. **Soll es eine separate Seite sein oder in die Leads-Seite integriert?**
   - Vorschlag: Separate Seite "Organisation" oder "Koordination"

2. **Wie genau soll die Priorisierung sein?**
   - Vorschlag: Automatisch basierend auf Credits/Fehlend

3. **Soll es Echtzeit-Updates geben?**
   - Vorschlag: Auto-Refresh alle 30 Sekunden

4. **Soll es eine "Quick-Action" geben, um direkt Leads zuzuweisen?**
   - Vorschlag: Ja, Button "Leads zuweisen" öffnet Lead-Liste gefiltert nach Makler-Gebiet

5. **Soll es Warnungen/Notifications geben?**
   - Vorschlag: Badge in Navigation wenn Makler wenig Credits haben

## Nächste Schritte

1. ✅ Plan erstellen (DIESES DOKUMENT)
2. ⏳ Plan mit Benutzer besprechen
3. ⏳ Backend-Service implementieren
4. ⏳ API-Endpunkte erstellen
5. ⏳ Frontend-Seite erstellen
6. ⏳ Integration in Navigation
7. ⏳ Testing








