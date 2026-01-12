# LeadGate CRM - Deployment-Anleitung

Diese Anleitung beschreibt, wie Sie LeadGate CRM für die Produktion vorbereiten und hosten.

---

## 📋 Voraussetzungen

- Python 3.11 oder höher
- Server mit mindestens 2GB RAM
- Domain mit SSL-Zertifikat (HTTPS erforderlich für Stripe)
- Stripe-Account (für Zahlungen)

---

## 🚀 Schritt-für-Schritt Deployment

### 1. Server vorbereiten

```bash
# System-Updates
sudo apt update && sudo apt upgrade -y

# Python installieren (falls nicht vorhanden)
sudo apt install python3 python3-pip python3-venv -y

# Firewall konfigurieren
sudo ufw allow 22/tcp   # SSH
sudo ufw allow 80/tcp   # HTTP
sudo ufw allow 443/tcp  # HTTPS
sudo ufw enable
```

### 2. Projekt auf Server kopieren

```bash
# Via Git
git clone <ihr-repository> /opt/leadgate
cd /opt/leadgate

# Oder via SCP/SFTP
# Kopieren Sie alle Dateien nach /opt/leadgate
```

### 3. Python-Umgebung einrichten

```bash
cd /opt/leadgate

# Virtuelle Umgebung erstellen
python3 -m venv venv

# Aktivieren
source venv/bin/activate

# Dependencies installieren
pip install --upgrade pip
pip install -r requirements.txt
```

### 4. Umgebungsvariablen konfigurieren

```bash
# Kopiere Beispiel-Datei
cp env.production.example .env

# Bearbeite .env-Datei
nano .env
```

**WICHTIGE Einstellungen in `.env`:**

```bash
# 1. JWT Secret Key generieren
python3 -c "import secrets; print(secrets.token_urlsafe(32))"
# Kopiere den generierten Key in JWT_SECRET_KEY=

# 2. CORS Origins setzen
ALLOWED_ORIGINS=https://ihre-domain.de

# 3. Frontend URL setzen
FRONTEND_URL=https://ihre-domain.de

# 4. Stripe LIVE-Keys eintragen
STRIPE_SECRET_KEY=sk_live_...
STRIPE_PUBLISHABLE_KEY=pk_live_...
STRIPE_WEBHOOK_SECRET=whsec_...

# 5. Environment auf production setzen
ENVIRONMENT=production
```

### 5. Datenbank initialisieren

```bash
# Datenbank wird beim ersten Start automatisch erstellt
# Optional: Backup der Entwicklung-Datenbank
# scp leadgate.db user@server:/opt/leadgate/
```

### 6. Systemd Service erstellen

Erstellen Sie `/etc/systemd/system/leadgate.service`:

```ini
[Unit]
Description=LeadGate CRM API Server
After=network.target

[Service]
Type=simple
User=www-data
WorkingDirectory=/opt/leadgate
Environment="PATH=/opt/leadgate/venv/bin"
ExecStart=/opt/leadgate/venv/bin/uvicorn backend.main:app --host 0.0.0.0 --port 8004 --workers 4
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

**Service aktivieren:**

```bash
sudo systemctl daemon-reload
sudo systemctl enable leadgate
sudo systemctl start leadgate
sudo systemctl status leadgate
```

### 7. Nginx Reverse Proxy einrichten

Installieren Sie Nginx:

```bash
sudo apt install nginx -y
```

Erstellen Sie `/etc/nginx/sites-available/leadgate`:

```nginx
server {
    listen 80;
    server_name ihre-domain.de www.ihre-domain.de;

    # Redirect HTTP zu HTTPS
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name ihre-domain.de www.ihre-domain.de;

    # SSL-Zertifikat (Let's Encrypt)
    ssl_certificate /etc/letsencrypt/live/ihre-domain.de/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/ihre-domain.de/privkey.pem;
    
    # SSL-Konfiguration
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;

    # Logs
    access_log /var/log/nginx/leadgate-access.log;
    error_log /var/log/nginx/leadgate-error.log;

    # Max Upload Size (für Datei-Uploads)
    client_max_body_size 50M;

    # Proxy zu FastAPI
    location / {
        proxy_pass http://127.0.0.1:8004;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # WebSocket Support (falls benötigt)
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        
        # Timeouts
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }

    # Health-Check direkt erreichbar
    location /health {
        proxy_pass http://127.0.0.1:8004/health;
        access_log off;
    }
}
```

**Nginx aktivieren:**

```bash
sudo ln -s /etc/nginx/sites-available/leadgate /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

### 8. SSL-Zertifikat (Let's Encrypt)

```bash
# Certbot installieren
sudo apt install certbot python3-certbot-nginx -y

# Zertifikat erstellen
sudo certbot --nginx -d ihre-domain.de -d www.ihre-domain.de

# Auto-Renewal testen
sudo certbot renew --dry-run
```

### 9. Stripe Webhook konfigurieren

1. Gehen Sie zu [Stripe Dashboard > Webhooks](https://dashboard.stripe.com/webhooks)
2. Klicken Sie auf "Add endpoint"
3. Endpoint URL: `https://ihre-domain.de/api/stripe/webhook`
4. Events auswählen:
   - `payment_intent.succeeded`
   - `payment_intent.payment_failed`
5. Signing secret kopieren und in `.env` als `STRIPE_WEBHOOK_SECRET` eintragen

### 10. Firewall & Sicherheit

```bash
# Nur notwendige Ports öffnen
sudo ufw allow 22/tcp   # SSH
sudo ufw allow 80/tcp   # HTTP (für Let's Encrypt)
sudo ufw allow 443/tcp  # HTTPS
sudo ufw enable

# Fail2Ban installieren (optional, aber empfohlen)
sudo apt install fail2ban -y
```

---

## 🔧 Wartung & Updates

### Logs ansehen

```bash
# Application Logs
tail -f /opt/leadgate/logs/leadgate.log

# Systemd Logs
sudo journalctl -u leadgate -f

# Nginx Logs
sudo tail -f /var/log/nginx/leadgate-access.log
sudo tail -f /var/log/nginx/leadgate-error.log
```

### Server neu starten

```bash
sudo systemctl restart leadgate
```

### Updates durchführen

```bash
cd /opt/leadgate
source venv/bin/activate

# Code aktualisieren (Git)
git pull

# Dependencies aktualisieren
pip install -r requirements.txt --upgrade

# Server neu starten
sudo systemctl restart leadgate
```

### Datenbank-Backup

```bash
# Backup erstellen
cp /opt/leadgate/leadgate.db /opt/leadgate/backups/leadgate_$(date +%Y%m%d_%H%M%S).db

# Automatisches Backup (Cronjob)
# Fügen Sie zu crontab hinzu: 0 2 * * * cp /opt/leadgate/leadgate.db /opt/leadgate/backups/leadgate_$(date +\%Y\%m\%d).db
```

---

## 📊 Monitoring

### Health-Check

```bash
# Lokal
curl http://localhost:8004/health

# Extern
curl https://ihre-domain.de/health
```

### Performance-Monitoring

- **Uptime**: `uptime`
- **Memory**: `free -h`
- **Disk**: `df -h`
- **Processes**: `htop` oder `top`

---

## 🚨 Troubleshooting

### Server startet nicht

```bash
# Logs prüfen
sudo journalctl -u leadgate -n 50

# Manuell starten zum Debuggen
cd /opt/leadgate
source venv/bin/activate
uvicorn backend.main:app --host 0.0.0.0 --port 8004
```

### Datenbank-Fehler

```bash
# Datenbank-Berechtigungen prüfen
ls -la /opt/leadgate/leadgate.db

# Datenbank reparieren (SQLite)
sqlite3 /opt/leadgate/leadgate.db "PRAGMA integrity_check;"
```

### Nginx-Fehler

```bash
# Konfiguration testen
sudo nginx -t

# Logs prüfen
sudo tail -f /var/log/nginx/error.log
```

---

## 🔐 Sicherheits-Checkliste

- [ ] JWT_SECRET_KEY geändert (nicht Standard-Wert)
- [ ] `.env` Datei nicht im Git (in `.gitignore`)
- [ ] HTTPS aktiviert (SSL-Zertifikat)
- [ ] Firewall konfiguriert
- [ ] CORS Origins korrekt gesetzt
- [ ] Stripe LIVE-Keys verwendet (nicht Test-Keys)
- [ ] Datenbank-Backups eingerichtet
- [ ] Logs regelmäßig überprüft
- [ ] System-Updates regelmäßig durchgeführt

---

## 📞 Support

Bei Problemen:
1. Logs prüfen (siehe oben)
2. Health-Check testen: `/health`
3. System-Status prüfen: `sudo systemctl status leadgate`

---

**Viel Erfolg mit LeadGate CRM!** 🚀

