# Anleitung: Stripe-Zahlung testen

## Problem: "Zahlung nicht verfügbar"

Wenn du die Meldung "Online-Zahlung ist derzeit nicht verfügbar" siehst, liegt das meist daran, dass:

1. **Der Server die .env-Datei nicht geladen hat** (Server neu starten!)
2. **Die Stripe-Keys nicht korrekt in der .env-Datei sind**

## Lösung: Server neu starten

1. **Stoppe den aktuellen Server** (Strg+C im Terminal)
2. **Starte den Server neu:**
   ```powershell
   cd C:\GateCRMLINK
   python -m uvicorn backend.main:app --reload
   ```

3. **Warte bis der Server gestartet ist** (siehst "Application startup complete")

## Testen der Zahlung

### Als Makler in GateLink einloggen:

1. Öffne GateLink: `http://localhost:8000/gatelink`
2. Logge dich als Makler ein (z.B. Juraj: `juraj@gmx.de`)
3. Klicke auf **"Credits aufladen"** (sollte oben angezeigt werden)
4. Gib einen Betrag ein (z.B. 100)
5. Klicke auf "OK"

### Erwartetes Verhalten:

✅ **Wenn Stripe aktiviert ist:**
- Ein Zahlungsmodal öffnet sich
- Du kannst Kreditkartendaten eingeben
- Test-Karte: `4242 4242 4242 4242`
- Ablaufdatum: beliebig zukünftiges Datum (z.B. 12/25)
- CVC: beliebige 3 Ziffern (z.B. 123)

❌ **Wenn Stripe NICHT aktiviert ist:**
- Meldung: "Online-Zahlung ist derzeit nicht verfügbar"

## Debugging: Prüfe ob Stripe aktiviert ist

Öffne die Browser-Konsole (F12) und schaue nach:

1. **Beim Klick auf "Credits aufladen":**
   - Wird `Fehler beim Prüfen der Stripe-Konfiguration` angezeigt?
   - Oder wird `Stripe-API Fehler` angezeigt?

2. **Manuell prüfen:**
   - Öffne: `http://localhost:8000/api/stripe/config`
   - Sollte zurückgeben: `{"enabled": true, "publishable_key": "pk_test_..."}`
   - Wenn `"enabled": false` → Server neu starten!

## Häufige Probleme

### Problem 1: Secret Key wird nicht geladen
**Symptom:** `STRIPE_ENABLED = False` obwohl Keys in .env vorhanden

**Lösung:**
1. Prüfe die .env-Datei - keine Zeilenumbrüche in den Keys!
2. Server neu starten
3. Prüfe ob `python-dotenv` installiert ist: `pip install python-dotenv`

### Problem 2: "Stripe ist nicht konfiguriert"
**Symptom:** API gibt 503 Fehler zurück

**Lösung:**
1. Prüfe ob beide Keys in .env vorhanden sind
2. Server neu starten
3. Prüfe Backend-Logs beim Server-Start

### Problem 3: Zahlungsmodal öffnet sich nicht
**Symptom:** Kein Modal, nur Alert

**Lösung:**
1. Browser-Konsole öffnen (F12)
2. Prüfe auf JavaScript-Fehler
3. Prüfe ob Stripe.js geladen wird

## Test-Kreditkarten (Stripe Test-Modus)

- **Erfolgreich:** `4242 4242 4242 4242`
- **Abgelehnt:** `4000 0000 0000 0002`
- **3D Secure:** `4000 0025 0000 3155`

Ablaufdatum: Beliebige zukünftige Daten (z.B. 12/25)
CVC: Beliebige 3 Ziffern (z.B. 123)








