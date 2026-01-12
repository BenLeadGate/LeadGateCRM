# Stripe Setup-Anleitung für LeadGate

Diese Anleitung führt dich Schritt für Schritt durch die Einrichtung von Stripe für das Credits-System.

## Schritt 1: Stripe-Account erstellen

1. Gehe zu: https://stripe.com/de
2. Klicke auf "Jetzt loslegen" oder "Konto erstellen"
3. Fülle das Formular aus:
   - E-Mail-Adresse
   - Passwort
   - Name
   - Land (Deutschland)
4. Bestätige deine E-Mail-Adresse (Check dein E-Mail-Postfach)

## Schritt 2: Test-Modus aktivieren

Stripe hat zwei Modi:
- **Test-Modus**: Für Entwicklung und Tests (kostenlos, keine echten Zahlungen)
- **Live-Modus**: Für echte Zahlungen (wird später aktiviert)

**Für den Anfang: Bleibe im Test-Modus!**

Du siehst oben rechts im Stripe-Dashboard einen Toggle "Test-Modus" / "Live-Modus". Stelle sicher, dass "Test-Modus" aktiviert ist.

## Schritt 3: API-Schlüssel (Keys) holen

1. Im Stripe-Dashboard, gehe zu: **Developers** → **API keys**
   (Oder direkt: https://dashboard.stripe.com/test/apikeys)

2. Du siehst zwei Schlüssel:
   - **Publishable key** (beginnt mit `pk_test_...`)
   - **Secret key** (beginnt mit `sk_test_...`)

3. **WICHTIG**: Klicke auf "Reveal test key" beim Secret key, um ihn anzuzeigen

4. Kopiere beide Keys und speichere sie sicher (z.B. in einer Textdatei)

## Schritt 4: Umgebungsvariablen setzen

### Option A: Windows PowerShell (Empfohlen für lokale Entwicklung)

Öffne PowerShell im Projektordner und führe aus:

```powershell
# Setze Stripe-Keys (ersetze die Werte mit deinen echten Keys!)
$env:STRIPE_SECRET_KEY="sk_test_dein_secret_key_hier"
$env:STRIPE_PUBLISHABLE_KEY="pk_test_dein_publishable_key_hier"

# Starte den Server
python -m uvicorn backend.main:app --reload
```

**WICHTIG**: Diese Variablen sind nur für diese PowerShell-Session gültig. Wenn du PowerShell schließt, musst du sie erneut setzen.

### Option B: Windows CMD

```cmd
set STRIPE_SECRET_KEY=sk_test_dein_secret_key_hier
set STRIPE_PUBLISHABLE_KEY=pk_test_dein_publishable_key_hier
python -m uvicorn backend.main:app --reload
```

### Option C: .env Datei (Besser für dauerhafte Nutzung)

1. Erstelle eine Datei namens `.env` im Projekt-Root (gleicher Ordner wie `requirements.txt`)

2. Füge folgende Zeilen ein (ersetze mit deinen echten Keys):

```
STRIPE_SECRET_KEY=sk_test_dein_secret_key_hier
STRIPE_PUBLISHABLE_KEY=pk_test_dein_publishable_key_hier
```

3. Installiere python-dotenv:
```bash
pip install python-dotenv
```

4. Ändere `backend/config.py` um die .env Datei zu laden (siehe unten)

## Schritt 5: .env Datei in Code einbinden (Optional, aber empfohlen)

Falls du die .env-Datei verwenden möchtest, ändere `backend/config.py`:

```python
import os
from dotenv import load_dotenv

# Lade .env Datei
load_dotenv()

# Stripe-Konfiguration
STRIPE_SECRET_KEY: Optional[str] = os.getenv("STRIPE_SECRET_KEY", None)
STRIPE_PUBLISHABLE_KEY: Optional[str] = os.getenv("STRIPE_PUBLISHABLE_KEY", None)
STRIPE_WEBHOOK_SECRET: Optional[str] = os.getenv("STRIPE_WEBHOOK_SECRET", None)
```

## Schritt 6: Webhook konfigurieren (Für Produktion wichtig)

**Für lokale Entwicklung kannst du diesen Schritt erstmal überspringen!**

Webhooks sind für die automatische Gutschrift nach erfolgreicher Zahlung wichtig.

### Für lokale Entwicklung (mit Stripe CLI):

1. Installiere Stripe CLI: https://stripe.com/docs/stripe-cli
2. Führe aus:
```bash
stripe listen --forward-to localhost:8000/api/stripe/webhook
```
3. Du bekommst einen Webhook-Secret (beginnt mit `whsec_...`)
4. Setze ihn als Umgebungsvariable:
```bash
$env:STRIPE_WEBHOOK_SECRET="whsec_dein_webhook_secret_hier"
```

### Für Produktion (mit echter Domain):

1. Im Stripe-Dashboard: **Developers** → **Webhooks**
2. Klicke auf "Add endpoint"
3. Endpoint URL: `https://deine-domain.de/api/stripe/webhook`
4. Wähle Events:
   - `payment_intent.succeeded`
   - `payment_intent.payment_failed`
5. Kopiere den "Signing secret" (beginnt mit `whsec_...`)
6. Setze ihn als Umgebungsvariable

## Schritt 7: Test-Zahlung durchführen

1. Starte den Server mit den Stripe-Keys
2. Gehe zu Makler-Verwaltung
3. Erstelle einen Makler mit "Prepaid-Credits" System
4. Klicke auf "Credits aufladen"
5. Wähle "Online mit Kreditkarte bezahlen"
6. Verwende Stripe Test-Karten:
   - **Erfolgreich**: `4242 4242 4242 4242`
   - **Abgelehnt**: `4000 0000 0000 0002`
   - Beliebiger Ablauf (z.B. 12/34)
   - Beliebige CVC (z.B. 123)
   - Beliebige PLZ (z.B. 12345)

## Schritt 8: Auf Live-Modus umstellen (Später)

Wenn du bereit für echte Zahlungen bist:

1. Im Stripe-Dashboard: Wechsle zu "Live-Modus"
2. Hole die Live-Keys (beginnen mit `pk_live_...` und `sk_live_...`)
3. Ersetze die Test-Keys mit Live-Keys
4. Konfiguriere Webhook für deine Produktions-Domain
5. **WICHTIG**: Teste gründlich im Test-Modus bevor du auf Live umstellst!

## Troubleshooting

### "Stripe ist nicht konfiguriert"
- Prüfe ob die Umgebungsvariablen gesetzt sind
- Starte den Server neu nach dem Setzen der Variablen
- Prüfe ob die Keys korrekt kopiert wurden (keine Leerzeichen am Anfang/Ende)

### "Invalid API Key"
- Stelle sicher, dass du im richtigen Modus bist (Test vs. Live)
- Prüfe ob der Key vollständig kopiert wurde
- Test-Keys beginnen mit `pk_test_` oder `sk_test_`

### Zahlung funktioniert nicht
- Prüfe Browser-Konsole auf Fehler
- Stelle sicher, dass Stripe.js geladen wird
- Prüfe ob der Payment Intent erfolgreich erstellt wurde

## Sicherheit

⚠️ **WICHTIG**: 
- **NIEMALS** die Secret Keys in Git committen!
- Füge `.env` zur `.gitignore` hinzu
- Verwende Test-Keys für Entwicklung
- Verwende Live-Keys nur in Produktion

## Weitere Hilfe

- Stripe Dokumentation: https://stripe.com/docs
- Stripe Support: https://support.stripe.com
- Test-Karten: https://stripe.com/docs/testing








