# LeadGate CRM & Abrechnung - Vollständige Dokumentation

## Inhaltsverzeichnis
1. [Übersicht](#übersicht)
2. [Design & Benutzeroberfläche](#design--benutzeroberfläche)
3. [Tools & Module](#tools--module)
4. [Funktionen im Detail](#funktionen-im-detail)
5. [Benutzerrollen & Berechtigungen](#benutzerrollen--berechtigungen)
6. [API-Endpunkte](#api-endpunkte)
7. [Technische Details](#technische-details)

---

## Übersicht

**LeadGate CRM & Abrechnung** ist eine lokal gehostete Webanwendung zur Verwaltung von Immobilienmaklern, Lead-Erfassung und automatischer monatlicher Abrechnung. Die Anwendung bietet ein modernes, Apple-inspiriertes Design mit umfassenden Funktionen für CRM, Abrechnung, Controlling und Kommunikation.

### Hauptfunktionen
- **Makler-Verwaltung**: Vollständige CRUD-Operationen für Immobilienmakler
- **Lead-Management**: Erfassung, Qualifizierung und Statusverwaltung von Leads
- **Automatische Abrechnung**: Monatliche Rechnungserstellung basierend auf gelieferten Leads
- **Controlling**: Zentrale Übersicht und Verwaltung aller Makler-Daten
- **Chat-System**: Interne Kommunikation zwischen Benutzern und Maklern
- **CSV-Import**: Massenimport von Leads aus CSV-Dateien
- **GateLink**: Externes Portal für Makler zur Lead-Verwaltung

---

## Design & Benutzeroberfläche

> **Hinweis**: Für detaillierte Design-Spezifikationen siehe [DESIGN_SYSTEM.md](DESIGN_SYSTEM.md) - Single Source of Truth für UI/UX.

### Design-Philosophie

Die Anwendung verwendet ein **Apple-inspiriertes Design** mit folgenden Charakteristika:

#### Farbpalette (Design Tokens)
- **Primärfarbe**: `#0071e3` (Apple Blue)
- **Text Primary**: `#1d1d1f` (Fast Schwarz)
- **Text Muted**: `#6b7280` (Grau)
- **Hintergrund**: `#fafafa` (Hellgrau)
- **Surface**: `#ffffff` (Weiß)
- **Border**: `#e5e7eb` (Hellgrau)
- **Semantic Colors**: Success `#16a34a`, Warning `#f59e0b`, Danger `#dc2626`

#### Typografie
- **Schriftart**: System-Schriftarten (`-apple-system, BlinkMacSystemFont, "SF Pro Display", system-ui, sans-serif`)
- **Schriftgrößen**: 
  - Überschriften: 5xl (48px) für Haupttitel
  - Untertitel: xl (20px)
  - Body-Text: base (16px)
  - Kleine Texte: sm (14px), xs (12px)

#### UI-Elemente

**Navigation**
- Sticky Navigation Bar mit Backdrop-Blur-Effekt (`bg-white/80 backdrop-blur-md`)
- Abgerundete Navigation-Items (`rounded-full`)
- Sanfte Hover-Übergänge (200ms ease-out)
- Aktiver Zustand durch grauen Hintergrund hervorgehoben (`bg-gray-100`)
- Primary CTA auf der rechten Seite

**Karten & Container**
- Weiße Karten mit subtilen Schatten (`shadow-sm` oder `shadow-md`)
- Border: 1px `gray-200` (`border border-gray-100`)
- Abgerundete Ecken: 24px (`rounded-2xl`)
- Padding: 24–32px (`p-6` bis `p-8`)
- Max Content Width: 1200px (`max-w-6xl`)

**Buttons**
- **Primär**: Blau (`bg-[#0071e3]`) mit weißem Text, `rounded-xl`, Hover: `opacity-90`
- **Sekundär**: Grau (`bg-gray-100`) mit `#1d1d1f` Text, Hover: `gray-200`
- **Destruktiv**: Rot (`bg-red-600`) - sparsam verwenden
- Größen: `px-6 py-3` für Standard, `px-5 py-3` für kompakt
- Active State: Subtile Scale (`scale-[0.99]`)

**Formulare**
- Input-Felder: Weißer Hintergrund, grauer Border (`border-gray-200`)
- Focus-State: Blauer Ring 2px (`focus:ring-2 focus:ring-[#0071e3]`), kein Outline
- Abgerundete Ecken: 16px (`rounded-xl`)
- Padding: `px-4 py-3`
- Placeholder: Muted Text (`text-gray-400`)

**Modals**
- Backdrop: Schwarzer Overlay 40% Opacity mit Blur (`bg-black/40 backdrop-blur-sm`)
- Modal-Container: Weiß, abgerundet 24px (`rounded-2xl`), Schatten (`shadow-2xl`)
- Animationen: Fade + Scale beim Öffnen
- Max Width: `max-w-md` für Standard-Modals

**Chat-Interface**
- Apple Messages-ähnliches Design
- Blaue Blasen für eigene Nachrichten (`bg-[#007AFF]`)
- Weiße Blasen für empfangene Nachrichten (`bg-white`)
- Abgerundete Ecken: 24px mit unterschiedlichen Radien (`rounded-3xl rounded-tr-sm`)
- Avatar-System: Farbige Avatare für Makler, Logo für LeadGate-Benutzer
- Datum-Trenner: Dezente Badges mit muted Text
- Lesebestätigung: Häkchen-Icon bei eigenen Nachrichten

---

## Tools & Module

### 1. Dashboard (`index.html`)

**Zweck**: Zentrale Übersicht über alle wichtigen Kennzahlen und Statistiken

**Hauptfunktionen**:
- **Statistik-Karten**: 
  - Aktive Makler
  - Qualifizierte Leads (gesamt und aktueller Monat)
  - Anzahl Rechnungen
  - Gesamtumsatz mit Durchschnitt pro Rechnung
- **Makler Lead-Übersicht**: 
  - Soll/Ist-Vergleich pro Monat
  - Vertragsmonat-Anzeige
  - Status-Badges (Erfüllt, Fast, Offen, Inaktiv)
  - Erfüllungsgrad in Prozent
- **Top Makler**: Liste der Makler mit den meisten gelieferten Leads
- **Monatliche Trends**: Visuelle Darstellung der Lead-Entwicklung über Monate
- **Qualifizierungen pro User**: Übersicht über qualifizierte Leads pro Benutzer (nur für Admin/Manager)

**Filter & Auswahl**:
- Monats- und Jahresauswahl für Statistiken
- Automatische Aktualisierung bei Änderungen

---

### 2. Makler-Verwaltung (`makler.html`)

**Zweck**: Verwaltung aller Immobilienmakler

**Hauptfunktionen**:
- **Makler-Liste**: 
  - Übersicht aller Makler mit Firmenname, Email, Status
  - Suchfunktion
  - Filter nach Status (Aktiv, Pausiert, Gekündigt)
- **Makler-Details**:
  - Vollständige Kontaktdaten
  - Vertragsdaten (Start, Ende, Pausierung)
  - Preiskonfiguration (Testphase, Standard)
  - Monatliche Soll-Leads
  - Gebiet (PLZ-Bereiche)
  - Notizen
- **Dokumentenverwaltung**:
  - Upload von Dokumenten (PDF, Bilder, etc.)
  - Download-Funktion
  - Beschreibungen zu Dokumenten
- **CRUD-Operationen**:
  - Neuen Makler anlegen
  - Makler bearbeiten
  - Makler löschen (mit Bestätigung)
  - Makler pausieren/reaktivieren

**Besondere Features**:
- GateLink-Passwort-Verwaltung für externen Zugang
- Rechnungs-Code für automatische Rechnungsnummerierung
- Vertragsmonat-Berechnung basierend auf Vertragsstart

---

### 3. Lead-Verwaltung (`leads.html`)

**Zweck**: Erfassung und Verwaltung von Immobilien-Leads

**Hauptfunktionen**:
- **Lead-Liste**:
  - Übersicht aller Leads mit Status, Makler, Datum
  - Erweiterte Suchfunktion (nach allen Feldern)
  - Filter nach Status, Makler, Datum
  - Sortierung nach verschiedenen Kriterien
- **Lead-Details**:
  - Anbieter-Informationen (Name, PLZ, Ort)
  - Immobilien-Daten (Flächen, Preis, Typ, Baujahr)
  - Kontaktdaten (Telefonnummer)
  - Features/Ausstattung
  - Status-Verwaltung (neu, qualifiziert, geliefert, storniert, reklamiert)
  - Makler-Zuordnung
  - Qualifizierungs-Informationen (User, Datum, Beschreibung)
  - Makler-Status (für GateLink)
  - Makler-Beschreibung
- **CRUD-Operationen**:
  - Neuen Lead erstellen
  - Lead bearbeiten
  - Lead löschen
  - Bulk-Operationen (mehrere Leads gleichzeitig)
- **Qualifizierung**:
  - Leads qualifizieren (Status ändern)
  - Beschreibung hinzufügen
  - Automatische Zeitstempel

**Status-Workflow**:
1. **Unqualifiziert** → Neuer Lead ohne Makler
2. **Qualifiziert** → Lead wurde geprüft und einem Makler zugeordnet
3. **Geliefert** → Lead wurde an Makler übergeben (wird für Abrechnung gezählt)
4. **Storniert** → Lead wurde storniert
5. **Reklamiert** → Makler hat Lead reklamiert

---

### 4. Abrechnung (`abrechnung.html`)

**Zweck**: Erstellung und Verwaltung von Rechnungen

**Hauptfunktionen**:
- **Rechnungsübersicht**:
  - Liste aller Rechnungen (monatlich und Beteiligungsrechnungen)
  - Suchfunktion
  - Status-Verwaltung (Offen, Überfällig, Bezahlt, Mahnungen, etc.)
  - PDF-Download
- **Monatsabrechnung erstellen**:
  - Auswahl von Makler, Monat und Jahr
  - Automatische Berechnung basierend auf:
    - Anzahl gelieferter Leads im Monat
    - Vertragsmonat (1. Monat = Testphase-Preis, ab 2. Monat = Standard-Preis)
    - Testphase-Leads werden abgezogen
- **Beteiligungsabrechnung**:
  - Erstellung für verkaufte Immobilien
  - Berechnung basierend auf Verkaufspreis und Beteiligungsprozent
  - Automatische Suche nach verkauften Leads ohne Rechnung
- **Rechnungsstatus**:
  - Offen
  - Überfällig
  - Bezahlt
  - Zahlungserinnerung gesendet
  - 1. Mahnung
  - 2. Mahnung
  - Mahnverfahren

**Preislogik**:
- **Vertragsmonat 1**: Verwendung des `testphase_preis`
- **Vertragsmonat 2+**: Verwendung des `standard_preis`
- Testphase-Leads werden vom Gesamtbetrag abgezogen

**PDF-Generierung**:
- Automatische Erstellung von PDF-Rechnungen
- Rechnungsnummer im Format: `LG-{Jahr}-{Monat}-{MaklerCode}{RechnungID}`
- Professionelles Layout mit allen Rechnungsdetails

---

### 5. Controlling (`controlling.html`)

**Zweck**: Zentrale Kontroll- und Verwaltungsfunktion für Makler (nur Admin/Manager)

**Hauptfunktionen**:
- **Makler-Auswahl**: Sidebar mit allen Maklern
- **Detailansicht** (nach Makler-Auswahl):
  - **Vertrag & Preise**: 
    - Vertragsstart/-ende (editierbar)
    - Pausierungs-Status (Toggle-Button)
    - Rechnungs-Code
    - Testphase- und Standard-Preise
    - Monatliche Soll-Leads
  - **Statistiken**:
    - Lead-Übersicht (Gesamt, Geliefert, Neu, Storniert)
    - Aktueller Monat (Soll/Ist-Vergleich)
    - Umsatz-Statistiken
  - **Gebiet & Notizen**:
    - PLZ-Bereiche (editierbar)
    - Notizen (editierbar)
  - **Kontaktdaten**:
    - Ansprechpartner, Email, Adresse (alle editierbar)
  - **Rechnungen**:
    - Liste aller Rechnungen des Maklers
    - Direkte Erstellung neuer Rechnungen
    - PDF-Download
  - **Dokumente**:
    - Liste aller hochgeladenen Dokumente
    - Download-Funktion
    - Link zur Dokumenten-Verwaltung
  - **Letzte Leads**:
    - Tabelle der letzten Leads
    - Direkter Link zur Bearbeitung

**Editier-Funktionen**:
- Klick auf editierbare Felder öffnet Eingabefeld
- Direktes Speichern über API
- Sofortige Aktualisierung der Anzeige

---

### 6. Upload (`upload.html`)

**Zweck**: CSV-Import von Leads

**Hauptfunktionen**:
- **Datei-Upload**:
  - Drag & Drop oder Dateiauswahl
  - Unterstützung für CSV-Dateien
  - Datei-Info-Anzeige (Name, Größe)
- **Import-Format**:
  - **Format 1 (Vertikal - EMPFOHLEN)**: 
    - Spalte A: Kategorie, Spalte B: Wert
    - Leads durch leere Zeilen getrennt
    - Einfach zu erstellen
  - **Format 2 (Horizontal)**:
    - Jede Zeile = ein Lead
    - Spalten = Kategorien
    - Erste Zeile = Spaltenüberschriften
- **Unterstützte Felder**:
  - Anbieter_Name (Pflicht)
  - Postleitzahl, Ort
  - Grundstücksfläche, Wohnfläche
  - Preis, Telefonnummer
  - Features (kommagetrennt)
  - Immobilien_Typ, Baujahr, Lage
  - Optional: Makler-Zuordnung
- **Import-Prozess**:
  - Validierung der CSV-Struktur
  - Fehlerbehandlung mit detaillierten Meldungen
  - Erfolgs-/Fehlerstatistik
  - Leads werden ohne Makler importiert (Status: Unqualifiziert)

**CSV-Format-Details**:
- Encoding: UTF-8
- Trennzeichen: Komma oder Semikolon (automatische Erkennung)
- Dezimalzahlen: Punkt oder Komma
- Preis-Format: Unterstützt deutsches Format (150.000,00 €)

---

### 7. Benutzer-Verwaltung (`benutzer.html`)

**Zweck**: Verwaltung von System-Benutzern (nur Admin/Manager)

**Hauptfunktionen**:
- **Benutzer-Liste**:
  - Übersicht aller Benutzer
  - Anzeige von ID, Benutzername, Email, Rolle, Status
  - Erstellungsdatum
- **Benutzer erstellen**:
  - Benutzername (Pflicht)
  - Email (optional, wird automatisch generiert falls leer)
  - Rolle (Telefonist, Buchhalter, Manager, Uploader, Admin)
  - Passwort (min. 6 Zeichen)
- **Benutzer-Verwaltung**:
  - Passwort zurücksetzen
  - Benutzer aktivieren/deaktivieren
  - Benutzer löschen (nur Admin)
- **Rollen-Verwaltung**:
  - Rolle ändern (nur Admin)

**Rollen**:
- **Admin**: Vollzugriff auf alle Funktionen
- **Manager**: Zugriff auf Controlling, Benutzer-Verwaltung, Chat mit Maklern
- **Buchhalter**: Zugriff auf Abrechnung, Makler, Leads
- **Telefonist**: Zugriff auf Leads, Makler (nur Lesen), Chat
- **Uploader**: Nur Zugriff auf Upload-Funktion

---

### 8. Chat-System

**Zweck**: Interne Kommunikation zwischen Benutzern und Maklern

**Hauptfunktionen**:
- **Konversations-Liste**:
  - Übersicht aller Chat-Konversationen
  - Letzte Nachricht und Zeitstempel
  - Ungelesene Nachrichten-Badge
  - Avatar-System (farbige Avatare für Makler, Logo für LeadGate)
- **Chat-Interface**:
  - Apple Messages-ähnliches Design
  - Blaue Blasen für eigene Nachrichten
  - Weiße Blasen für empfangene Nachrichten
  - Datum-Trenner
  - Zeitstempel
  - Lesebestätigung (Häkchen)
- **Neue Konversation**:
  - Auswahl zwischen Benutzern und Maklern
  - Rollenbasierte Filterung (Telefonisten sehen nur Manager/Admin)
- **Echtzeit-Updates**:
  - Auto-Refresh alle 5 Sekunden
  - Ungelesene Nachrichten-Badge in Navigation
  - Optimistic Updates (Nachricht sofort anzeigen)

**Berechtigungen**:
- Alle Rollen können Chat verwenden
- Telefonisten/Buchhalter: Nur mit Manager/Admin
- Manager/Admin: Mit allen Benutzern und Maklern

---

### 9. GateLink Dashboard (`gatelink_dashboard.html`)

**Zweck**: Externes Portal für Makler zur Lead-Verwaltung

**Hauptfunktionen**:
- **Makler-Login**: 
  - Separate Authentifizierung mit Email und GateLink-Passwort
  - JWT-Token-basiert
- **Lead-Übersicht**:
  - Nur Leads des eingeloggten Maklers
  - Filter nach Status
  - Suchfunktion
- **Lead-Status**:
  - In Gesprächen
  - Erstkontakt stattgefunden
  - Nicht funktioniert
  - Reklamation
  - Unter Maklervertrag
  - Immobilie verkauft
- **Makler-Beschreibung**:
  - Eigene Notizen zu jedem Lead
  - Getrennt von Telefonist-Beschreibung
- **Chat mit LeadGate**:
  - Direkte Kommunikation mit LeadGate-Team
  - Nachrichten-Historie

**Sicherheit**:
- Separate Authentifizierung
- Nur Zugriff auf eigene Leads
- GateLink-Passwort muss vom Admin gesetzt werden

---

## Funktionen im Detail

### Authentifizierung & Autorisierung

**Login-System**:
- JWT-Token-basierte Authentifizierung
- Token-Speicherung im LocalStorage
- Automatische Token-Validierung bei API-Requests
- Redirect zur Login-Seite bei ungültigem Token

**Rollenbasierte Zugriffskontrolle**:
- Navigation passt sich automatisch an Rolle an
- API-Endpunkte prüfen Berechtigungen
- Fehlermeldungen bei unberechtigtem Zugriff

### Datenbank-Modelle

**Makler**:
- Firmenname, Ansprechpartner, Email, Adresse
- Vertragsdaten (Start, Ende, Pausierung)
- Preiskonfiguration (Testphase, Standard)
- Monatliche Soll-Leads
- Gebiet (PLZ-Bereiche)
- Notizen
- GateLink-Passwort
- Rechnungs-Code

**Lead**:
- Anbieter-Informationen
- Immobilien-Daten
- Kontaktdaten
- Status
- Makler-Zuordnung
- Qualifizierungs-Informationen
- Makler-Status und -Beschreibung
- Verkaufs-Informationen (für Beteiligungsrechnung)

**Rechnung**:
- Rechnungstyp (monatlich, beteiligung)
- Makler-Zuordnung
- Monat/Jahr (für Monatsrechnung)
- Anzahl Leads
- Gesamtbetrag
- Status
- Erstellungsdatum

**User**:
- Benutzername, Email
- Hashed Password
- Rolle
- Aktiv-Status
- Erstellungsdatum

**ChatMessage**:
- Absender (User oder Makler)
- Empfänger (User oder Makler)
- Nachricht
- Zeitstempel
- Gelesen-Status

### Abrechnungslogik

**Vertragsmonat-Berechnung**:
- Basierend auf Vertragsstart-Datum
- Relativ zum Abrechnungsmonat
- Beispiel: Vertragsstart 15.01.2025, Abrechnung Januar 2025 = Vertragsmonat 1

**Preisberechnung**:
- Vertragsmonat 1: `testphase_preis` pro Lead
- Vertragsmonat 2+: `standard_preis` pro Lead
- Testphase-Leads werden vom Gesamtbetrag abgezogen
- Formel: `(Anzahl gelieferte Leads - Testphase-Leads) × Preis pro Lead`

**Beteiligungsrechnung**:
- Wird erstellt wenn:
  - Lead-Status = "Immobilie verkauft"
  - Verkaufspreis vorhanden
  - Beteiligungsprozent vorhanden
  - Noch keine Beteiligungsrechnung existiert
- Berechnung: `Verkaufspreis × (Beteiligungsprozent / 100)`

### Export-Funktionen

**CSV-Export**:
- Makler-Export
- Leads-Export
- Rechnungen-Export
- Alle mit UTF-8 Encoding
- Deutsche Formatierung (Komma als Dezimaltrennzeichen)

---

## Benutzerrollen & Berechtigungen

### Admin
- **Vollzugriff** auf alle Funktionen
- Benutzer-Verwaltung (erstellen, löschen, Rollen ändern)
- Controlling-Zugriff
- Chat mit allen Benutzern und Maklern
- Alle CRUD-Operationen

### Manager
- Zugriff auf:
  - Dashboard
  - Makler (vollständig)
  - Leads (vollständig)
  - Controlling
  - Abrechnung (nur ansehen, nicht erstellen)
  - Benutzer-Verwaltung
  - Chat (mit allen Benutzern und Maklern)
- **Kein Zugriff** auf:
  - Rechnungserstellung (nur Buchhalter/Admin)

### Buchhalter
- Zugriff auf:
  - Dashboard
  - Makler (vollständig)
  - Leads (vollständig)
  - Abrechnung (inkl. Erstellung)
  - Chat (nur mit Manager/Admin)
- **Kein Zugriff** auf:
  - Controlling
  - Benutzer-Verwaltung

### Telefonist
- Zugriff auf:
  - Dashboard
  - Makler (nur Lesen)
  - Leads (vollständig, kann qualifizieren)
  - Chat (nur mit Manager/Admin)
- **Kein Zugriff** auf:
  - Abrechnung
  - Controlling
  - Benutzer-Verwaltung

### Uploader
- Zugriff auf:
  - Upload-Funktion
- **Kein Zugriff** auf:
  - Alle anderen Funktionen

---

## API-Endpunkte

### Authentifizierung (`/api/auth`)
- `POST /register` - Benutzer registrieren
- `POST /login` - Login und Token erhalten
- `GET /me` - Aktueller Benutzer
- `POST /users` - Neuen Benutzer erstellen
- `GET /users` - Alle Benutzer auflisten
- `PUT /users/{id}/password` - Passwort ändern
- `PUT /users/{id}/status` - Status ändern
- `PUT /users/{id}/role` - Rolle ändern
- `DELETE /users/{id}` - Benutzer löschen
- `POST /chat` - Nachricht senden
- `GET /chat/conversations` - Konversationen auflisten
- `GET /chat/conversations/{type}/{id}` - Nachrichten einer Konversation

### Makler (`/api/makler`)
- `GET /` - Alle Makler auflisten
- `GET /{id}` - Einzelnen Makler abrufen
- `POST /` - Neuen Makler erstellen
- `PUT /{id}` - Makler aktualisieren
- `DELETE /{id}` - Makler löschen
- `GET /{id}/controlling` - Controlling-Daten
- `POST /{id}/dokumente` - Dokument hochladen
- `GET /{id}/dokumente` - Dokumente auflisten
- `GET /{id}/dokumente/{doc_id}/download` - Download
- `DELETE /{id}/dokumente/{doc_id}` - Dokument löschen

### Leads (`/api/leads`)
- `GET /` - Alle Leads auflisten
- `GET /{id}` - Einzelnen Lead abrufen
- `POST /` - Neuen Lead erstellen
- `PUT /{id}` - Lead aktualisieren
- `DELETE /{id}` - Lead löschen
- `POST /bulk` - Mehrere Leads erstellen

### Rechnungen (`/api/rechnungen`)
- `GET /` - Alle Rechnungen auflisten
- `GET /{id}` - Einzelne Rechnung abrufen
- `GET /{id}/pdf` - PDF herunterladen
- `POST /monat/{makler_id}` - Monatsabrechnung erstellen
- `POST /beteiligung` - Beteiligungsabrechnung erstellen
- `PATCH /{id}/status` - Status aktualisieren
- `GET /verkaufte-leads` - Verkaufte Leads ohne Rechnung

### Statistiken (`/api/statistiken`)
- `GET /dashboard` - Dashboard-Statistiken
- `GET /qualifizierungen-pro-user` - Qualifizierungen pro User

### Makler-Statistiken (`/api/makler-stats`)
- `GET /mit-statistiken` - Makler mit Statistiken
- `GET /monatsstatistik` - Monatsstatistik für alle Makler

### Export (`/api/export`)
- `GET /makler/csv` - Makler als CSV
- `GET /leads/csv` - Leads als CSV
- `GET /rechnungen/csv` - Rechnungen als CSV

### Upload (`/api/upload`)
- `POST /upload` - Datei hochladen
- `GET /upload/files` - Dateien auflisten
- `GET /upload/files/{id}/download` - Download
- `DELETE /upload/files/{id}` - Datei löschen
- `POST /upload/import-leads` - Leads aus CSV importieren

### GateLink (`/api/gatelink`)
- `POST /login` - Makler-Login
- `GET /me` - Aktueller Makler
- `GET /leads` - Leads des Maklers
- `PUT /leads/{id}` - Lead aktualisieren
- `POST /leads/{id}/reklamieren` - Lead reklamieren
- `POST /chat` - Nachricht senden
- `GET /chat` - Nachrichten abrufen

---

## Technische Details

### Backend
- **Framework**: FastAPI (Python)
- **Datenbank**: SQLite mit SQLAlchemy ORM
- **Authentifizierung**: JWT (python-jose)
- **Passwort-Hashing**: bcrypt
- **PDF-Generierung**: reportlab
- **API-Dokumentation**: Automatisch unter `/docs` (Swagger UI) und `/redoc`

### Frontend
- **Framework**: Vanilla JavaScript
- **Styling**: TailwindCSS (via CDN)
- **Design System**: Apple-inspired (siehe [DESIGN_SYSTEM.md](DESIGN_SYSTEM.md))
- **Icons**: SVG (inline)
- **State Management**: LocalStorage für Token
- **API-Communication**: Fetch API mit automatischem Token-Handling
- **Motion**: Subtile Animationen (150–250ms, ease-out)

### Datenbank-Schema
- **Tabellen**: 
  - `users` - System-Benutzer
  - `makler` - Immobilienmakler
  - `leads` - Immobilien-Leads
  - `rechnungen` - Rechnungen
  - `chat_messages` - Chat-Nachrichten
  - `makler_dokumente` - Dokumente
- **Beziehungen**:
  - Makler → Leads (1:n)
  - Makler → Rechnungen (1:n)
  - User → Leads (Qualifizierung, 1:n)
  - User/Makler → ChatMessages (1:n)

### Sicherheit
- Passwort-Hashing mit bcrypt
- JWT-Token mit Ablaufzeit
- Rollenbasierte Zugriffskontrolle
- SQL-Injection-Schutz durch ORM
- XSS-Schutz durch HTML-Escaping
- CORS-Konfiguration (aktuell: alle Origins erlaubt - sollte in Produktion eingeschränkt werden)

### Performance
- Datenbank-Indizes auf häufig abgefragten Feldern
- Lazy Loading für große Listen
- Optimistic Updates im Frontend
- Auto-Refresh für Chat (alle 5 Sekunden)

---

## Zusammenfassung

LeadGate CRM & Abrechnung ist eine umfassende Lösung für die Verwaltung von Immobilienmaklern und Leads mit modernem Design, rollenbasierter Zugriffskontrolle und automatischer Abrechnung. Die Anwendung bietet sowohl interne Verwaltungsfunktionen als auch ein externes Portal für Makler.

**Hauptstärken**:
- Intuitives, Apple-inspiriertes Design
- Umfassende Funktionalität
- Flexible Rollen- und Berechtigungssystem
- Automatische Abrechnungslogik
- Integriertes Chat-System
- CSV-Import für Massendaten

**Technologie-Stack**:
- Backend: Python/FastAPI
- Frontend: Vanilla JS/TailwindCSS
- Datenbank: SQLite
- Authentifizierung: JWT

Die Anwendung ist für den lokalen Betrieb optimiert und kann einfach über uvicorn gestartet werden.

