# Preislogik Optimierungsplan

## Aktuelle Situation

### Altes System (Monatliche Rechnungen)
- **Vertragsmonat 1**: `testphase_preis` pro Lead
- **Ab Vertragsmonat 2**: `standard_preis` pro Lead
- **Problem**: `testphase_leads` wird NICHT berücksichtigt - alle Leads im ersten Monat werden zum Testphase-Preis berechnet
- **Problem**: Keine klare Erklärung im Frontend

### Credits-System (Prepaid)
- **Vertragsmonat 1, erste X Leads**: `erste_leads_preis` pro Lead
- **Vertragsmonat 1, Leads über X**: `erste_leads_danach_preis` pro Lead
- **Ab Vertragsmonat 2**: `standard_preis` pro Lead
- **Problem**: Logik ist komplex, aber nicht visuell dargestellt
- **Problem**: Keine Beispiel-Berechnung
- **Problem**: Unklar was bei Pausen/Kündigungen passiert

## Identifizierte Probleme

### 1. Unklare Feldbeschreibungen
- ❌ "Testphase Leads" - unklar ob das die Anzahl ist, die zum Testphase-Preis berechnet werden
- ❌ "Erste X Leads" - nicht klar genug erklärt
- ❌ Keine visuelle Darstellung der Preisstruktur

### 2. Altes System ignoriert `testphase_leads`
- Aktuell: ALLE Leads im ersten Monat = Testphase-Preis
- Sollte sein: Erste X Leads = Testphase-Preis, danach = Standard-Preis

### 3. Keine Beispiele/Berechnungen
- Nutzer versteht nicht, wie sich die Preise zusammensetzen
- Keine Vorschau der Kosten

### 4. Pausen/Kündigungen unklar
- Was passiert wenn Vertrag pausiert wird?
- Was passiert nach Kündigung?
- Wann startet die Preislogik neu?

### 5. Keine Validierung der Logik
- Testphase-Preis sollte < Standard-Preis sein (sonst macht es keinen Sinn)
- Erste Leads Preis sollte < Danach Preis sein (sonst macht es keinen Sinn)

## Optimierungsvorschläge

### Priorität 1: Altes System korrigieren

1. **Testphase-Leads berücksichtigen**
   - Im ersten Monat: Erste `testphase_leads` Leads = `testphase_preis`
   - Im ersten Monat: Leads über `testphase_leads` = `standard_preis`
   - Ab 2. Monat: Alle Leads = `standard_preis`

2. **`bestimme_preis_pro_lead()` erweitern**
   - Braucht zusätzlichen Parameter: `anzahl_leads_im_monat`
   - Prüft ob `anzahl_leads_im_monat <= testphase_leads`

### Priorität 2: Frontend-Verbesserungen

3. **Visuelle Preisstruktur-Darstellung**
   - Info-Box mit Beispiel:
     ```
     Beispiel bei 10 Leads im 1. Monat:
     - Erste 5 Leads × 50€ = 250€
     - Nächste 5 Leads × 75€ = 375€
     - Gesamt: 625€
     
     Ab 2. Monat: Alle Leads × 100€
     ```

4. **Bessere Feldbeschreibungen**
   - Testphase Leads: "Anzahl der Leads, die im ersten Monat zum Testphase-Preis berechnet werden"
   - Erste X Leads: "Anzahl der Leads, die im ersten Monat zum reduzierten Preis berechnet werden"

5. **Validierung hinzufügen**
   - Testphase-Preis sollte < Standard-Preis (Warnung)
   - Erste Leads Preis sollte < Danach Preis (Warnung)
   - Erste Leads Preis sollte < Standard-Preis (Warnung)

### Priorität 3: Klarstellungen

6. **Pausen/Kündigungen dokumentieren**
   - Info-Box: "Bei Vertragspause oder nach Kündigung werden keine Leads mehr berechnet"
   - "Die Preislogik startet ab Vertragsstart-Datum"

7. **Dynamische Beispiel-Berechnung**
   - JavaScript berechnet automatisch ein Beispiel
   - Zeigt Gesamtkosten für verschiedene Szenarien

## Umsetzungsplan

### Schritt 1: Backend - Altes System korrigieren
- `bestimme_preis_pro_lead()` erweitern
- `finde_oder_erzeuge_rechnung()` anpassen
- `berechne_durchschnittlichen_preis()` prüfen

### Schritt 2: Frontend - Visuelle Darstellung
- Info-Boxen mit Beispielen
- Dynamische Berechnung
- Bessere Beschreibungen

### Schritt 3: Validierung
- Client-seitige Validierung
- Warnungen bei unlogischen Preisen

### Schritt 4: Dokumentation
- Kommentare im Code
- Klarere Hilfetexte


