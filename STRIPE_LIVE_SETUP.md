# Stripe Live-Modus Setup

## ✅ Schritt 1: Live-Keys gespeichert

Die Live-Keys wurden in der `.env`-Datei gespeichert:
- Secret Key: `sk_live_...`
- Publishable Key: `pk_live_...`

## ⚠️ WICHTIG: Webhook konfigurieren

Für automatische Credits-Gutschrift nach erfolgreicher Zahlung musst du einen Webhook in Stripe konfigurieren.

### Webhook einrichten:

1. **Gehe zu Stripe-Dashboard**: https://dashboard.stripe.com/webhooks
2. **Klicke auf "Add endpoint"**
3. **Endpoint URL eingeben**: 
   ```
   https://deine-domain.de/api/stripe/webhook
   ```
   (Ersetze `deine-domain.de` mit deiner echten Domain)
   
   **Für lokale Tests mit ngrok:**
   ```
   https://dein-ngrok-url.ngrok.io/api/stripe/webhook
   ```

4. **Events auswählen**:
   - ✅ `payment_intent.succeeded` (wichtig!)
   - ✅ `payment_intent.payment_failed` (optional, für Fehlerbehandlung)

5. **"Add endpoint" klicken**

6. **Signing secret kopieren**:
   - Nach dem Erstellen des Webhooks siehst du einen "Signing secret"
   - Beginnt mit `whsec_...`
   - Kopiere diesen Wert

7. **In .env-Datei speichern**:
   ```
   STRIPE_WEBHOOK_SECRET=whsec_dein_webhook_secret_hier
   ```

## 🔄 Server neu starten

Nach dem Speichern der Keys und des Webhook-Secrets:

```powershell
# Server stoppen (Strg+C)
# Dann neu starten:
cd C:\GateCRMLINK
python -m uvicorn backend.main:app --reload
```

## ✅ Testen

1. **Als Makler in GateLink einloggen**
2. **Credits aufladen** (z.B. 5 Leads)
3. **Echte Kreditkarte eingeben**
4. **Zahlung abschließen**
5. **Prüfen**:
   - Credits sollten automatisch gutgeschrieben werden
   - In Stripe-Dashboard: Zahlung sollte sichtbar sein
   - Geld landet auf deinem Stripe-Konto

## 💰 Geld-Auszahlung

- **Automatisch**: Täglich, wöchentlich oder monatlich (einstellbar in Stripe)
- **Manuell**: Jederzeit im Stripe-Dashboard
- **Dauer**: 2-7 Werktage bis auf deinem Bankkonto

## ⚠️ Wichtige Hinweise

1. **HTTPS erforderlich**: Webhooks funktionieren nur über HTTPS (nicht HTTP)
2. **Domain verifizieren**: Stripe muss deine Domain erreichen können
3. **Webhook-Secret**: WICHTIG für Sicherheit - nie öffentlich machen!
4. **Testen**: Teste zuerst mit kleinen Beträgen

## 🔍 Webhook testen

Im Stripe-Dashboard kannst du:
- Webhook-Events sehen
- Test-Events senden
- Logs prüfen

## 📊 Stripe-Dashboard

Überwache deine Zahlungen:
- https://dashboard.stripe.com/payments
- https://dashboard.stripe.com/balance (Guthaben)
- https://dashboard.stripe.com/payouts (Auszahlungen)








