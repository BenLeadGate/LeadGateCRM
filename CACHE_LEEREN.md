# Browser-Cache leeren - Anleitung

## Problem: Änderungen werden nicht angezeigt

Die HTML-Datei wurde aktualisiert, aber der Browser zeigt noch die alte Version an. Das liegt am Browser-Cache.

## Lösung 1: Hard Reload (Schnellste Methode)

1. **Drücke `Ctrl + Shift + R`** (Windows/Linux)
   - Oder: `Ctrl + F5`
   - Das lädt die Seite komplett neu OHNE Cache

## Lösung 2: DevTools Cache leeren

1. Öffne die **Entwicklertools** (F12)
2. Rechtsklick auf den **Reload-Button** im Browser
3. Wähle **"Empty Cache and Hard Reload"** oder **"Cache leeren und hart neu laden"**

## Lösung 3: Browser-Cache komplett leeren

1. Drücke `Ctrl + Shift + Delete`
2. Wähle Zeitraum: **"Alle Zeit"** oder **"Letzte Stunde"**
3. Aktiviere **"Bilder und Dateien im Cache"**
4. Klicke auf **"Daten löschen"**
5. Lade die Seite neu (F5)

## Lösung 4: Inkognito-Modus testen

1. Öffne ein **Inkognito-Fenster** (`Ctrl + Shift + N`)
2. Gehe zu: `http://localhost:8004/makler.html`
3. Die neue Version sollte dort sofort sichtbar sein

## Lösung 5: URL mit Zeitstempel

Füge `?v=2` oder `?nocache=123` an die URL an:
- `http://localhost:8004/makler.html?v=2`

Das zwingt den Browser, die Datei neu zu laden.

## Lösung 6: Service Worker deaktivieren (falls vorhanden)

1. Öffne DevTools (F12)
2. Gehe zu **Application** → **Service Workers**
3. Klicke auf **"Unregister"** falls ein Service Worker aktiv ist

---

## Beste Methode für Entwickler:

**Verwende immer `Ctrl + Shift + R`** beim Testen von Änderungen!


