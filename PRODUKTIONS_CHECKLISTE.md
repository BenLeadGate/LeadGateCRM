# ✅ Produktions-Checkliste für LeadGate CRM

Verwenden Sie diese Checkliste, bevor Sie das System in Produktion bringen.

---

## 🔐 Sicherheit

- [ ] **JWT_SECRET_KEY** geändert (nicht Standard-Wert)
  - Generieren mit: `python -c "import secrets; print(secrets.token_urlsafe(32))"`
  - In `.env` Datei eintragen

- [ ] **.env Datei** erstellt und konfiguriert
  - Kopiert von `env.production.example`
  - Alle Werte gesetzt

- [ ] **.env Datei** ist in `.gitignore` (nicht im Git)

- [ ] **CORS Origins** korrekt gesetzt
  - Nur Ihre Domain(s) erlaubt
  - Keine `*` oder `localhost` in Produktion

- [ ] **HTTPS/SSL** aktiviert
  - SSL-Zertifikat installiert (Let's Encrypt empfohlen)
  - HTTP zu HTTPS Redirect konfiguriert

- [ ] **Firewall** konfiguriert
  - Nur notwendige Ports offen (22, 80, 443)
  - Port 8004 nicht öffentlich erreichbar (nur via Nginx)

---

## 💳 Stripe-Konfiguration

- [ ] **Stripe LIVE-Keys** verwendet (nicht Test-Keys)
  - `STRIPE_SECRET_KEY` beginnt mit `sk_live_`
  - `STRIPE_PUBLISHABLE_KEY` beginnt mit `pk_live_`

- [ ] **Stripe Webhook** konfiguriert
  - Endpoint URL: `https://ihre-domain.de/api/stripe/webhook`
  - Events: `payment_intent.succeeded`, `payment_intent.payment_failed`
  - `STRIPE_WEBHOOK_SECRET` in `.env` eingetragen

- [ ] **Stripe-Verbindung** getestet
  - Payment Intent kann erstellt werden
  - Webhook-Events werden empfangen

---

## ⚙️ Konfiguration

- [ ] **ENVIRONMENT=production** in `.env` gesetzt

- [ ] **ALLOWED_ORIGINS** auf Produktions-Domain gesetzt
  - Format: `https://ihre-domain.de` (kein Trailing Slash)

- [ ] **FRONTEND_URL** auf Produktions-Domain gesetzt
  - Format: `https://ihre-domain.de`

- [ ] **LOG_LEVEL=INFO** für Produktion
  - Nicht DEBUG in Produktion (Performance & Sicherheit)

- [ ] **RATE_LIMIT_ENABLED=true** aktiviert
  - Schutz vor Brute-Force-Angriffen

---

## 🗄️ Datenbank

- [ ] **Datenbank** initialisiert
  - `leadgate.db` existiert
  - Alle Tabellen erstellt

- [ ] **Datenbank-Backup** eingerichtet
  - Automatisches Backup konfiguriert (Cronjob)
  - Backup-Verzeichnis erstellt

- [ ] **Datenbank-Berechtigungen** korrekt
  - Datei ist beschreibbar für den Server-User

---

## 🚀 Server-Konfiguration

- [ ] **Systemd Service** erstellt und aktiviert
  - Service-Datei: `/etc/systemd/system/leadgate.service`
  - Service läuft: `sudo systemctl status leadgate`

- [ ] **Nginx Reverse Proxy** konfiguriert
  - Konfiguration: `/etc/nginx/sites-available/leadgate`
  - SSL-Zertifikat konfiguriert
  - Proxy zu `http://127.0.0.1:8004`

- [ ] **Server startet automatisch** nach Reboot
  - `sudo systemctl enable leadgate`

- [ ] **Mehrere Workers** konfiguriert
  - Mindestens 4 Workers für Produktion
  - In Systemd Service: `--workers 4`

---

## 📁 Verzeichnisse & Dateien

- [ ] **logs/** Verzeichnis existiert und ist beschreibbar

- [ ] **uploads/** Verzeichnis existiert und ist beschreibbar

- [ ] **makler_dokumente/** Verzeichnis existiert und ist beschreibbar

- [ ] **backups/** Verzeichnis existiert

---

## 🧪 Tests

- [ ] **Health-Check** funktioniert
  - `curl https://ihre-domain.de/health`
  - Antwort: `{"status":"healthy","database":"connected"}`

- [ ] **API-Endpunkte** erreichbar
  - `curl https://ihre-domain.de/api/stripe/config`
  - Antwort enthält Stripe-Konfiguration

- [ ] **Frontend** lädt korrekt
  - `https://ihre-domain.de/` zeigt Login-Seite

- [ ] **Login** funktioniert
  - Kann sich mit Admin-User einloggen

- [ ] **Stripe-Zahlung** getestet (Test-Zahlung)
  - Payment Intent kann erstellt werden
  - Webhook wird empfangen

---

## 📊 Monitoring

- [ ] **Logs** werden geschrieben
  - `tail -f /opt/leadgate/logs/leadgate.log`

- [ ] **System-Monitoring** eingerichtet (optional)
  - Uptime-Monitoring
  - Error-Tracking (z.B. Sentry)

- [ ] **Backup-Monitoring** eingerichtet
  - Backup wird regelmäßig erstellt
  - Backup wird getestet (Restore-Test)

---

## 📝 Dokumentation

- [ ] **Deployment-Dokumentation** gelesen
  - `DEPLOYMENT.md` durchgearbeitet

- [ ] **Admin-Zugangsdaten** dokumentiert
  - Username: `ben`
  - Passwort sicher gespeichert (Passwort-Manager)

- [ ] **Kontakt-Informationen** dokumentiert
  - Support-Kontakt
  - Server-Zugangsdaten (sicher gespeichert)

---

## 🔄 Nach Deployment

- [ ] **Erste Zahlung** getestet (kleiner Betrag)
  - Stripe-Zahlung durchgeführt
  - Credits wurden gutgeschrieben

- [ ] **Webhook** getestet
  - Stripe sendet Events
  - Events werden verarbeitet

- [ ] **Backup** getestet
  - Backup erstellt
  - Restore getestet

- [ ] **Performance** überprüft
  - Seiten laden schnell
  - API-Antwortzeiten akzeptabel

---

## ✅ Finale Prüfung

- [ ] **Alle Checklisten-Punkte** abgehakt

- [ ] **System läuft stabil** seit mindestens 24 Stunden

- [ ] **Keine kritischen Fehler** in den Logs

- [ ] **Team informiert** über Produktions-URL und Zugangsdaten

---

**Viel Erfolg mit dem Deployment!** 🚀

Bei Fragen oder Problemen: Siehe `DEPLOYMENT.md` → Troubleshooting

