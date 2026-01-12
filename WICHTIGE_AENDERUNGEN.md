# ⚠️ WICHTIG: Was Sie jetzt anders machen müssen

## 🔐 1. JWT Secret Key setzen (KRITISCH!)

**Was ist passiert?**
- Der JWT Secret Key wird jetzt aus einer Umgebungsvariable geladen
- Der alte hardcodierte Key war unsicher

**Was müssen Sie tun?**
1. Öffnen Sie die Datei `.env` im Projektverzeichnis
2. Finden Sie die Zeile: `JWT_SECRET_KEY=your-secret-key-change-this-in-production`
3. Ersetzen Sie den Wert durch einen sicheren, zufälligen String (mindestens 32 Zeichen)

**Beispiel:**
```env
JWT_SECRET_KEY=MeinSicheresGeheimnis1234567890abcdefghijklmnop
```

**Warum wichtig?**
- Ohne sicheren Key können Angreifer Tokens fälschen
- Jeder mit dem Key kann sich als beliebiger Benutzer ausgeben
- **MUSS in Produktion geändert werden!**

---

## 🌐 2. CORS Origins anpassen

**Was ist passiert?**
- CORS erlaubt jetzt nur noch spezifische Domains (nicht mehr alle)

**Was müssen Sie tun?**
1. Öffnen Sie die Datei `.env`
2. Finden Sie: `ALLOWED_ORIGINS=http://localhost:8004,http://127.0.0.1:8004`
3. Fügen Sie Ihre Produktions-Domains hinzu (kommagetrennt)

**Beispiel für Produktion:**
```env
ALLOWED_ORIGINS=https://ihre-domain.de,https://www.ihre-domain.de
```

**Warum wichtig?**
- Verhindert, dass fremde Websites Ihre API nutzen können
- Schützt vor Cross-Site-Request-Forgery (CSRF) Angriffen

---

## 🔑 3. Neues Admin-Passwort

**Was ist passiert?**
- Das Standard-Passwort "admin123" wurde durch ein zufälliges Passwort ersetzt
- Das neue Passwort wird beim Serverstart generiert

**Was müssen Sie tun?**
1. Starten Sie den Server
2. Schauen Sie in die Konsole/Logs - dort steht das neue Passwort
3. Loggen Sie sich mit Benutzername "ben" und dem neuen Passwort ein
4. **Ändern Sie das Passwort sofort nach dem ersten Login!**

**Wo finde ich das Passwort?**
- In der PowerShell-Konsole, in der der Server läuft
- Oder in der Datei `logs/leadgate.log`

**Ausgabe sieht so aus:**
```
================================================================================
⚠️  WICHTIG: Admin-User 'ben' wurde erstellt
   Standard-Passwort: AbCdEf1234567890
   BITTE ÄNDERN SIE DAS PASSWORT NACH DEM ERSTEN LOGIN!
================================================================================
```

---

## 🔒 4. GateLink-Passwörter

**Was ist passiert?**
- GateLink-Passwörter werden jetzt gehasht (wie normale Passwörter)
- Alte Klartext-Passwörter werden automatisch beim Login gehasht

**Was müssen Sie tun?**
- **Nichts!** Die Migration läuft automatisch
- Beim ersten Login eines Maklers wird das Passwort automatisch gehasht
- Alte Passwörter funktionieren weiterhin (werden beim Login migriert)

**Hinweis:**
- Wenn Sie ein neues GateLink-Passwort setzen, wird es automatisch gehasht
- Sie können das Passwort nicht mehr im Klartext sehen (aus Sicherheitsgründen)

---

## ⏱️ 5. Token-Ablaufzeit geändert

**Was ist passiert?**
- Access Tokens laufen jetzt nach 24 Stunden ab (vorher 30 Tage)
- Refresh Tokens laufen nach 30 Tagen ab

**Was müssen Sie tun?**
- **Nichts!** Funktioniert automatisch
- Das Frontend sollte Refresh Tokens verwenden, um neue Access Tokens zu holen

**Neue API-Endpunkte:**
- `POST /api/auth/refresh` - Erstellt neues Access Token mit Refresh Token

**Frontend-Anpassung (optional):**
- Wenn das Frontend Token-Refresh implementiert, wird der Benutzer nicht mehr abgemeldet
- Aktuell: Nach 24 Stunden muss sich der Benutzer neu einloggen

---

## 🚦 6. Rate Limiting aktiv

**Was ist passiert?**
- Login-Endpoint hat jetzt Rate Limiting
- Maximal 5 Login-Versuche pro Minute pro IP-Adresse

**Was müssen Sie tun?**
- **Nichts!** Funktioniert automatisch
- Bei zu vielen Versuchen: 429 Fehler "Zu viele Login-Versuche"

**Konfiguration (optional):**
- In `.env` können Sie anpassen:
  ```env
  RATE_LIMIT_ENABLED=true
  RATE_LIMIT_PER_MINUTE=5
  ```

---

## 📊 7. Pagination bei Listen

**Was ist passiert?**
- Listen-Endpunkte haben jetzt Pagination
- Standard: 100 Einträge pro Seite

**Was müssen Sie tun?**
- **Frontend anpassen:** API-Aufrufe müssen `skip` und `limit` Parameter verwenden

**Beispiel:**
```
GET /api/makler?skip=0&limit=100
GET /api/leads?skip=100&limit=100
GET /api/rechnungen?skip=0&limit=50
```

**Parameter:**
- `skip`: Anzahl zu überspringender Einträge (Standard: 0)
- `limit`: Maximale Anzahl zurückzugebender Einträge (Standard: 100, Max: 1000)

---

## 📝 8. Logging statt Debug-Prints

**Was ist passiert?**
- Debug-Print-Statements wurden durch strukturiertes Logging ersetzt

**Was müssen Sie tun?**
- **Nichts!** Funktioniert automatisch
- Logs werden in `logs/leadgate.log` gespeichert
- Auch in der Konsole sichtbar

**Log-Levels:**
- `DEBUG`: Detaillierte Informationen (nur in Entwicklung)
- `INFO`: Wichtige Informationen
- `WARNING`: Warnungen
- `ERROR`: Fehler

---

## 🏥 9. Health-Check Endpoint

**Was ist passiert?**
- Neuer `/health` Endpoint für Monitoring

**Was müssen Sie tun?**
- **Nichts!** Kann für Monitoring verwendet werden

**Verwendung:**
```
GET http://localhost:8004/health
```

**Antwort:**
```json
{
  "status": "healthy",
  "database": "connected",
  "environment": "development"
}
```

---

## ✅ Checkliste

- [ ] `.env` Datei erstellt und `JWT_SECRET_KEY` geändert
- [ ] `ALLOWED_ORIGINS` in `.env` angepasst (für Produktion)
- [ ] Server neu gestartet
- [ ] Neues Admin-Passwort aus Logs notiert
- [ ] Mit neuem Passwort eingeloggt
- [ ] Admin-Passwort geändert
- [ ] Frontend für Pagination angepasst (optional)
- [ ] Frontend für Refresh Token angepasst (optional)

---

## 🆘 Hilfe

**Problem: "JWT Secret Key Warnung"**
- Lösung: Setzen Sie `JWT_SECRET_KEY` in `.env`

**Problem: "CORS Fehler"**
- Lösung: Fügen Sie Ihre Domain zu `ALLOWED_ORIGINS` in `.env` hinzu

**Problem: "Admin-Passwort nicht gefunden"**
- Lösung: Schauen Sie in `logs/leadgate.log` oder Server-Konsole

**Problem: "Rate Limiting zu streng"**
- Lösung: Erhöhen Sie `RATE_LIMIT_PER_MINUTE` in `.env`

---

## 📞 Support

Bei Fragen oder Problemen:
1. Prüfen Sie die Logs in `logs/leadgate.log`
2. Prüfen Sie die Server-Konsole
3. Prüfen Sie die `.env` Datei






