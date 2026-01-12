# Makler-Bearbeitung Optimierungsplan

## Analyse der aktuellen Situation

### Gefundene Felder im Formular:
1. **Grunddaten**
   - Firmenname ✓
   - Ansprechpartner ✓
   - Email ✓
   - Adresse ✓

2. **Vertragsdetails**
   - Vertragsstart ✓
   - Testphase Leads & Preis ✓
   - Standard Preis ✓
   - Monatliche Soll-Leads ✓

3. **Rechnungssystem**
   - Rechnungssystem-Typ (alt/neu) ✓
   - Credits-Preislogik (nur wenn "neu") ✓
     - Erste X Leads Anzahl
     - Preis für erste X Leads
     - Preis danach im 1. Monat

4. **Vertragsverwaltung**
   - Vertrag pausieren ✓
   - Vertrag bis (Kündigungsdatum) ✓

5. **Weitere Felder**
   - Rechnungs-Code ✓
   - Gebiet (Postleitzahlen) ✓
   - Notizen ✓
   - GateLink Passwort ✓

## Identifizierte Probleme

### 🔴 Kritische Probleme

1. **Automatische Aufladung fehlt im Formular**
   - Backend unterstützt `automatische_aufladung_aktiv`, `automatische_aufladung_betrag`, `automatische_aufladung_tag`
   - Frontend zeigt diese Felder nicht an
   - **Impact**: Funktionalität existiert im Backend, kann aber nicht konfiguriert werden

2. **GateLink Passwort als Text-Feld**
   - Aktuell: `<input type="text">` 
   - **Problem**: Passwort ist im Klartext sichtbar
   - **Lösung**: `<input type="password">` mit Option "Passwort anzeigen"

### 🟡 Wichtige Probleme

3. **Testphase-Felder beim Credits-System**
   - Testphase Leads/Preis werden auch angezeigt, wenn Rechnungssystem = "neu" (Credits)
   - **Problem**: Diese Felder haben bei Credits-System keine Bedeutung (wird ignoriert)
   - **Lösung**: Testphase-Felder nur anzeigen wenn Rechnungssystem = "alt"

4. **Fehlende Validierung**
   - Keine Validierung ob Preise >= 0
   - Keine Validierung ob Vertragsstart <= Vertrag bis
   - Keine Validierung ob Postleitzahlen-Format korrekt ist
   - Keine Validierung ob automatische Aufladung Tag zwischen 1-28 liegt

5. **Verwirrende Feld-Logik**
   - Wenn Rechnungssystem = "neu", sind Testphase-Felder irrelevant
   - Wenn Rechnungssystem = "alt", sind Credits-Preislogik-Felder irrelevant
   - **Problem**: Zu viele Felder sichtbar, die nicht relevant sind

### 🟢 Kleinere Verbesserungen

6. **Gebiet-Validierung verbessern**
   - Aktuell: Nur Text-Eingabe
   - **Verbesserung**: Live-Validierung der PLZ-Format (5-stellig, nur Zahlen)
   - **Verbesserung**: Hinweis bei zu vielen PLZ (Limit: 50)

7. **Standard-Preis bei Credits-System**
   - Aktuell: Wird immer angezeigt
   - **Verbesserung**: Hinweis, dass Standard-Preis ab 2. Monat verwendet wird

8. **Vertrag pausieren vs. Vertrag bis**
   - **Verbesserung**: Klarere Erklärung wann was verwendet wird
   - **Verbesserung**: Warnung wenn beide gesetzt sind (pausiert UND Kündigungsdatum)

9. **Erste Leads Anzahl Validierung**
   - **Verbesserung**: Minimum 1, Maximum sinnvoll begrenzen (z.B. 100)

10. **Monatliche Soll-Leads**
    - **Verbesserung**: Bessere Beschreibung was das bedeutet
    - **Verbesserung**: Warnung wenn 0 eingegeben wird

## Optimierungsvorschläge

### Priorität 1: Kritisch

1. **Automatische Aufladung hinzufügen**
   - Sektion "Automatische Aufladung" im Formular hinzufügen
   - Nur anzeigen wenn Rechnungssystem = "neu"
   - Felder:
     - Checkbox: "Automatische Aufladung aktivieren"
     - Betrag (€)
     - Tag des Monats (1-28)
   - Validierung: Betrag > 0 wenn aktiviert, Tag zwischen 1-28

2. **GateLink Passwort als Password-Feld**
   - `type="password"` verwenden
   - Optional: "Passwort anzeigen/verstecken" Toggle-Button

### Priorität 2: Wichtig

3. **Bedingte Anzeige von Feldern**
   - Testphase-Felder: Nur bei Rechnungssystem = "alt"
   - Credits-Preislogik: Nur bei Rechnungssystem = "neu"
   - Automatische Aufladung: Nur bei Rechnungssystem = "neu"

4. **Validierungen hinzufügen**
   - Client-seitige Validierung:
     - Preise >= 0
     - Vertragsstart <= Vertrag bis (wenn gesetzt)
     - PLZ-Format (5-stellig)
     - Automatische Aufladung Tag: 1-28
   - Fehlermeldungen unter den Feldern anzeigen

5. **Bessere Hilfetexte**
   - Jedes Feld hat einen hilfreichen Tooltip/Hinweis
   - Erklären wann welche Felder verwendet werden

### Priorität 3: Nice-to-have

6. **PLZ-Validierung verbessern**
   - Live-Validierung während Eingabe
   - Automatische Formatierung (Kommas/Zeilenumbrüche)
   - Zähler: "X von 50 PLZ eingegeben"

7. **Zusammenhänge besser erklären**
   - Info-Boxen erklären die Logik:
     - "Bei Credits-System: Erste X Leads kosten Y€, danach Z€, ab 2. Monat Standard-Preis"
     - "Bei altem System: Testphase-Leads werden zum Testphase-Preis berechnet, danach Standard-Preis"

8. **Warnungen bei Konflikten**
   - Warnung wenn Vertrag pausiert UND Vertrag bis gesetzt
   - Warnung wenn Testphase-Felder bei Credits-System ausgefüllt sind

## Empfohlene Umsetzung

### Schritt 1: Automatische Aufladung hinzufügen
- Frontend-Formular erweitern
- JavaScript-Logik für Anzeige/Verstecken
- Validierung hinzufügen

### Schritt 2: GateLink Passwort sicherer machen
- Password-Feld implementieren
- Optional: Toggle-Funktion

### Schritt 3: Bedingte Feld-Anzeige
- Testphase-Felder nur bei "alt"
- Credits-Preislogik nur bei "neu"
- Automatische Aufladung nur bei "neu"

### Schritt 4: Validierungen
- Client-seitige Validierung
- Fehlermeldungen anzeigen

### Schritt 5: UX-Verbesserungen
- Bessere Hilfetexte
- PLZ-Validierung
- Warnungen

## Technische Details

### Neue HTML-Struktur für automatische Aufladung:
```html
<div id="automatische-aufladung-section" class="md:col-span-2 hidden border-t border-gray-200 pt-6 mt-2">
    <h4 class="text-sm font-semibold text-[#1d1d1f] mb-4">Automatische Aufladung</h4>
    <div class="space-y-4">
        <label class="flex items-center space-x-3 cursor-pointer">
            <input type="checkbox" id="automatische_aufladung_aktiv" onchange="toggleAutomatischeAufladung()">
            <span>Automatische monatliche Aufladung aktivieren</span>
        </label>
        <div id="automatische-aufladung-felder" class="hidden grid grid-cols-2 gap-4">
            <div>
                <label>Betrag (€)</label>
                <input type="number" id="automatische_aufladung_betrag" step="0.01" min="0">
            </div>
            <div>
                <label>Tag des Monats (1-28)</label>
                <input type="number" id="automatische_aufladung_tag" min="1" max="28">
            </div>
        </div>
    </div>
</div>
```

### JavaScript-Funktionen benötigt:
- `toggleRechnungssystemFields()` - bereits vorhanden, muss erweitert werden
- `toggleAutomatischeAufladung()` - neu
- Validierungs-Funktionen - neu


