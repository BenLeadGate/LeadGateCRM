# GateLink Dashboard Verbesserung - Plan

## Anforderungen

### 1. Makler-Status für Leads
Makler sollen den Status jedes Leads setzen können mit folgenden Optionen:
- **In Gesprächen** - Makler ist in aktiven Gesprächen mit dem Lead
- **Erstkontakt stattgefunden** - Erster Kontakt wurde hergestellt
- **Nicht funktioniert** - Lead hat nicht funktioniert (z.B. falsche Nummer, nicht interessiert)
- **Reklamation** - Makler möchte den Lead reklamieren
- **Unter Maklervertrag** - Lead hat einen Maklervertrag abgeschlossen
- **Immobilie verkauft** - Makler hat die Immobilie erfolgreich verkauft

### 2. Makler-Beschreibung
- Makler sollen zu jedem Lead eine eigene Beschreibung/Notizen hinzufügen können
- Diese ist getrennt von der Telefonist-Beschreibung
- Makler können ihre Beschreibung jederzeit bearbeiten

### 3. Filter & Sortierung
- **Filter nach Status**: Dropdown/Buttons zum Filtern nach Makler-Status
- **Sortierung**: Nach Datum (neueste/älteste), nach Status
- **Suchfunktion**: Nach Anbieter, Ort, PLZ, Telefonnummer suchen

### 4. Visualisierung
- **Status-Badges**: Farbcodierte Badges für jeden Status
- **Kartenansicht**: Übersichtliche Lead-Karten mit allen wichtigen Infos
- **Detailansicht**: Modal/Dropdown mit vollständigen Lead-Details
- **Statistiken**: Übersicht über Anzahl Leads pro Status

## Technische Umsetzung

### Backend-Änderungen

1. **Lead-Modell erweitern** (`backend/models/lead.py`):
   - Neues Feld: `makler_status` (String, nullable) - Status vom Makler gesetzt
   - Neues Feld: `makler_beschreibung` (String, nullable) - Beschreibung vom Makler
   - Neues Feld: `makler_status_geaendert_am` (DateTime, nullable) - Wann wurde Status geändert

2. **Datenbank-Migration** (`backend/database.py`):
   - Migration für neue Felder hinzufügen

3. **Schemas erweitern** (`backend/schemas.py`):
   - `makler_status` und `makler_beschreibung` zu Lead-Schemas hinzufügen

4. **GateLink API erweitern** (`backend/routers/gatelink.py`):
   - `PUT /api/gatelink/leads/{lead_id}` - Makler kann Status und Beschreibung aktualisieren
   - Nur für Leads, die dem Makler zugeordnet sind

### Frontend-Änderungen

1. **Lead-Karten verbessern** (`frontend/gatelink_dashboard.html`):
   - Status-Badge mit Farben anzeigen
   - Button zum Öffnen der Detailansicht
   - Schnell-Status-Änderung direkt auf der Karte

2. **Lead-Detail-Modal**:
   - Alle Lead-Informationen anzeigen
   - Status-Dropdown zum Ändern
   - Textfeld für Makler-Beschreibung
   - Speichern-Button

3. **Filter & Sortierung**:
   - Filter-Buttons/Dropdown oben
   - Sortierung-Optionen
   - Suchfeld

4. **Statistiken-Banner**:
   - Anzahl Leads pro Status
   - Gesamtanzahl qualifizierter Leads

## Status-Farben (Vorschlag)

- **In Gesprächen**: Blau
- **Erstkontakt stattgefunden**: Grün
- **Nicht funktioniert**: Rot
- **Reklamation**: Orange
- **Unter Maklervertrag**: Lila
- **Immobilie verkauft**: Gold/Grün

## Implementierungsreihenfolge

1. Backend: Felder zum Modell hinzufügen + Migration
2. Backend: API-Endpunkt für Update
3. Frontend: Lead-Karten mit Status-Badges
4. Frontend: Detail-Modal mit Status- und Beschreibungs-Editierung
5. Frontend: Filter und Sortierung
6. Frontend: Statistiken




