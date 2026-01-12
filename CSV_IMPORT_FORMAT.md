# CSV-Import Format für Leads

## Übersicht
Diese Dokumentation beschreibt das erwartete Format für CSV-Dateien, die zum Importieren von Leads verwendet werden.

**Das System unterstützt zwei Formate:**
1. **Horizontales Format**: Jede Zeile = ein Lead, Spalten = Kategorien
2. **Vertikales Format**: Spalte A = Kategorie, Spalte B = Wert (empfohlen für einfache Erstellung)

## Erforderliche Spalten

Die CSV-Datei muss folgende Spalten enthalten (Spaltenüberschriften in der ersten Zeile):

| Spaltenname | Beschreibung | Beispiel | Optional |
|------------|--------------|----------|----------|
| **Anbieter_Name** | Name des Anbieters/Maklers | "Immobilien GmbH" | Nein |
| **Postleitzahl** | Postleitzahl der Immobilie | "12345" | Ja |
| **Ort** | Stadt/Ort der Immobilie | "Berlin" | Ja |
| **Grundstücksfläche** | Grundstücksfläche in m² | "500" oder "500.5" | Ja |
| **Wohnfläche** | Wohnfläche in m² | "120" oder "120.5" | Ja |
| **Preis** | Preis in Euro | "150000" oder "150.000,00 €" | Ja |
| **Telefonnummer** | Telefonnummer des Leads | "+49 30 12345678" | Ja |
| **Features** | Ausstattungsmerkmale (kommagetrennt) | "Keller, Balkon, Garten" | Ja |
| **Immobilien_Typ** | Typ der Immobilie | "Eigentumswohnung", "Haus", "Grundstück" | Ja |
| **Baujahr** | Baujahr der Immobilie | "1995" | Ja |
| **Lage** | Lagebeschreibung | "Ruhige Lage", "Zentrumsnah" | Ja |

## Optionale Makler-Spalte

Falls nicht alle Leads dem gleichen Makler zugeordnet werden sollen, kann eine zusätzliche Spalte hinzugefügt werden:

| Spaltenname | Beschreibung | Beispiel |
|------------|--------------|----------|
| **Makler_ID** | ID des Maklers (Zahl) | "1" |
| **Makler_Name** | Firmenname des Maklers | "Immobilien GmbH" |
| **Makler_Email** | E-Mail-Adresse des Maklers | "info@immobilien.de" |

## Beispiel-CSV

```csv
Anbieter_Name,Postleitzahl,Ort,Grundstücksfläche,Wohnfläche,Preis,Telefonnummer,Features,Immobilien_Typ,Baujahr,Lage
Immobilien GmbH,10115,Berlin,500,120,250000,+49 30 12345678,"Keller, Balkon, Garten",Haus,1995,"Ruhige Lage, zentrumsnah"
Haus & Grund,20095,Hamburg,300,80,180000,+49 40 98765432,Balkon,Eigentumswohnung,2010,Zentrumsnah
Wohnungsgesellschaft,80331,München,200,65,320000,+49 89 55555555,"Keller, Garten",Haus,1985,Ruhig
```

## Format 2: Vertikales Format (Kategorie, Wert) - EMPFOHLEN

**Einfacheres Format zum Erstellen:** Spalte A = Kategorie, Spalte B = Wert

### Beispiel:

```csv
Kategorie,Wert
Anbieter_Name,Immobilien GmbH
Postleitzahl,10115
Ort,Berlin
Grundstücksfläche,500
Wohnfläche,120
Preis,250000
Telefonnummer,+49 30 12345678
Features,"Keller, Balkon, Garten"
Immobilien_Typ,Haus
Baujahr,1995
Lage,Ruhige Lage, zentrumsnah

Anbieter_Name,Haus & Grund
Postleitzahl,20095
Ort,Hamburg
Grundstücksfläche,300
Wohnfläche,80
Preis,180000
Telefonnummer,+49 40 98765432
Features,Balkon
Immobilien_Typ,Eigentumswohnung
Baujahr,2010
Lage,Zentrumsnah
```

**Wichtig:**
- Erste Zeile: `Kategorie,Wert` (oder `Category,Value`)
- Jeder Lead wird durch eine **leere Zeile** getrennt
- Die Reihenfolge der Kategorien ist egal
- Nicht alle Kategorien müssen vorhanden sein (optional)

## Beispiel mit Makler-Spalte (horizontales Format)

```csv
Makler_Name,Anbieter_Name,Postleitzahl,Ort,Grundstücksfläche,Wohnfläche,Preis,Telefonnummer,Features
Immobilien GmbH,Immobilien GmbH,10115,Berlin,500,120,250000,+49 30 12345678,"Keller, Balkon, Garten"
Haus & Grund,Haus & Grund,20095,Hamburg,300,80,180000,+49 40 98765432,"Balkon"
```

## Wichtige Hinweise

1. **Encoding**: Die CSV-Datei sollte UTF-8 kodiert sein (mit oder ohne BOM)
2. **Trennzeichen**: Komma (`,`) oder Semikolon (`;`) als Spaltentrennzeichen - das System erkennt automatisch das verwendete Trennzeichen
3. **Textqualifizierung**: Mehrzeilige Werte oder Werte mit Kommas sollten in Anführungszeichen gesetzt werden
4. **Dezimalzahlen**: Verwenden Sie Punkt (`.`) oder Komma (`,`) als Dezimaltrennzeichen - beide werden akzeptiert
5. **Preis-Format**: Preise können in verschiedenen Formaten angegeben werden (z.B. "150000", "150.000,00", "150.000,00 €"). Das System unterstützt deutsches Format mit Punkt als Tausender-Trenner und Komma als Dezimaltrennzeichen
6. **Leere Felder**: Leere Felder sind erlaubt und werden als `null` gespeichert
7. **Erste Zeile**: Die erste Zeile muss die Spaltenüberschriften enthalten

## Spaltennamen-Varianten

Das System erkennt verschiedene Schreibweisen der Kategorienamen (case-insensitive):

### Für horizontales Format (Spaltenüberschriften):
- **Anbieter_Name**: `Anbieter_Name`, `Anbieter`, `Name`, `Anbieter Name`
- **Postleitzahl**: `Postleitzahl`, `PLZ`
- **Ort**: `Ort`, `Stadt`, `Wohnort`
- **Grundstücksfläche**: `Grundstücksfläche`, `Grundstuecksflaeche`, `Grundstücksfläche (m²)`, `Grundstücksfläche m²`
- **Wohnfläche**: `Wohnfläche`, `Wohnflaeche`, `Wohnfläche (m²)`, `Wohnfläche m²`
- **Preis**: `Preis`, `Preis (€)`, `Preis (Euro)`, `Preis €`, `Preis in Euro`, `Preis in €`
- **Telefonnummer**: `Telefonnummer`, `Telefon`, `Tel`, `Handy`
- **Features**: `Features`, `Ausstattung`, `Merkmale`, `Eigenschaften`
- **Immobilien_Typ**: `Immobilien_Typ`, `Immobilientyp`, `Immobilien Typ`, `Typ`
- **Baujahr**: `Baujahr`, `Baujahr (JJJJ)`
- **Lage**: `Lage`, `Lagebeschreibung`

### Für vertikales Format (Kategorie-Spalte):
- **Anbieter_Name**: `Anbieter_Name`, `Anbieter`, `Name`
- **Postleitzahl**: `Postleitzahl`, `PLZ`
- **Ort**: `Ort`, `Stadt`, `Wohnort`
- **Grundstücksfläche**: `Grundstücksfläche`, `Grundstuecksflaeche`, `Grundstücksflaeche`
- **Wohnfläche**: `Wohnfläche`, `Wohnflaeche`
- **Preis**: `Preis`, `Preis (€)`, `Preis (Euro)`, `Preis €`
- **Telefonnummer**: `Telefonnummer`, `Telefon`, `Tel`, `Handy`
- **Features**: `Features`, `Ausstattung`, `Merkmale`, `Eigenschaften`
- **Immobilien_Typ**: `Immobilien_Typ`, `Immobilientyp`, `Immobilien Typ`, `Typ`
- **Baujahr**: `Baujahr`, `Baujahr (JJJJ)`
- **Lage**: `Lage`, `Lagebeschreibung`
- **Makler**: `Makler_ID`, `Makler_Name`, `Makler_Email`, `Makler`

## Import-Prozess

1. Laden Sie die CSV-Datei über die Upload-Seite hoch
2. Wählen Sie optional einen Makler aus (falls nicht in CSV angegeben)
3. Klicken Sie auf "Leads importieren"
4. Das System zeigt eine Zusammenfassung mit erfolgreichen Imports und Fehlern an

## Fehlerbehandlung

Falls beim Import Fehler auftreten:
- Die Zeile wird übersprungen
- Eine Fehlermeldung wird in der Zusammenfassung angezeigt
- Erfolgreich importierte Leads werden trotzdem gespeichert

Häufige Fehler:
- Makler nicht gefunden: Stellen Sie sicher, dass der Makler im System existiert
- Ungültiges Format: Überprüfen Sie die CSV-Struktur
- Fehlende Pflichtfelder: Stellen Sie sicher, dass alle erforderlichen Spalten vorhanden sind

