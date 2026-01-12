from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from typing import List, Optional
import os
import shutil
from datetime import datetime
from pathlib import Path
import csv
import io
import random
import time

from ..database import get_db
from ..models.user import User
from ..models.lead import Lead
from ..models.makler import Makler
from ..services.auth_service import get_current_active_user, require_manager_or_telefonist
from ..models.user import UserRole
from .. import schemas

router = APIRouter()

# Upload-Verzeichnis erstellen
UPLOAD_DIR = Path(__file__).parent.parent.parent / "uploads"
UPLOAD_DIR.mkdir(exist_ok=True)


@router.post("/upload")
async def upload_files(
    files: List[UploadFile] = File(...),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Lädt eine oder mehrere Dateien hoch.
    """
    uploaded_files = []
    
    for file in files:
        try:
            # Dateiname sicher machen (keine Pfad-Traversal-Angriffe)
            safe_filename = os.path.basename(file.filename)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{timestamp}_{safe_filename}"
            file_path = UPLOAD_DIR / filename
            
            # Datei speichern
            with open(file_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
            
            uploaded_files.append({
                "filename": safe_filename,
                "saved_filename": filename,
                "size": file_path.stat().st_size,
                "uploaded_at": datetime.now().isoformat()
            })
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Fehler beim Speichern der Datei {file.filename}: {str(e)}"
            )
    
    return {
        "message": f"{len(uploaded_files)} Datei(en) erfolgreich hochgeladen",
        "files": uploaded_files
    }


@router.get("/upload/files")
async def list_uploaded_files(
    current_user: User = Depends(get_current_active_user)
):
    """
    Listet alle hochgeladenen Dateien auf.
    """
    files = []
    
    if not UPLOAD_DIR.exists():
        return files
    
    for file_path in UPLOAD_DIR.iterdir():
        if file_path.is_file():
            stat = file_path.stat()
            files.append({
                "id": file_path.name,  # Verwende Dateinamen als ID
                "filename": file_path.name,
                "size": stat.st_size,
                "uploaded_at": datetime.fromtimestamp(stat.st_mtime).isoformat()
            })
    
    # Sortiere nach Upload-Datum (neueste zuerst)
    files.sort(key=lambda x: x["uploaded_at"], reverse=True)
    
    return files


@router.get("/upload/files/{file_id}/download")
async def download_file(
    file_id: str,
    current_user: User = Depends(get_current_active_user)
):
    """
    Lädt eine Datei herunter.
    """
    file_path = UPLOAD_DIR / file_id
    
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Datei nicht gefunden")
    
    return FileResponse(
        path=str(file_path),
        filename=file_id,
        media_type="application/octet-stream"
    )


@router.delete("/upload/files/{file_id}")
async def delete_file(
    file_id: str,
    current_user: User = Depends(get_current_active_user)
):
    """
    Löscht eine Datei.
    """
    file_path = UPLOAD_DIR / file_id
    
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Datei nicht gefunden")
    
    try:
        file_path.unlink()
        return {"message": "Datei erfolgreich gelöscht"}
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Fehler beim Löschen der Datei: {str(e)}"
        )


def detect_delimiter(content: str) -> str:
    """Erkennt das Trennzeichen einer CSV-Datei (Komma oder Semikolon)."""
    # Prüfe erste nicht-leere Zeile
    lines = content.strip().split('\n')
    for line in lines[:5]:  # Prüfe erste 5 Zeilen
        if not line.strip():
            continue
        
        # Zähle Kommas und Semikolons
        comma_count = line.count(',')
        semicolon_count = line.count(';')
        
        # Wenn mehr Semikolons als Kommas, verwende Semikolon
        if semicolon_count > comma_count:
            print(f"[DEBUG CSV] Semikolon als Trennzeichen erkannt (Kommas: {comma_count}, Semikolons: {semicolon_count})")
            return ';'
        
        # Wenn Kommas vorhanden sind, verwende Komma
        if comma_count > 0:
            print(f"[DEBUG CSV] Komma als Trennzeichen erkannt (Kommas: {comma_count}, Semikolons: {semicolon_count})")
            return ','
    
    # Standard: Komma
    print(f"[DEBUG CSV] Standard-Trennzeichen verwendet: Komma")
    return ','


def parse_csv_file(file_content: bytes) -> List[dict]:
    """Parst eine CSV-Datei und gibt eine Liste von Dictionaries zurück.
    Unterstützt zwei Formate:
    1. Horizontal: Jede Zeile = ein Lead, Spalten = Kategorien
    2. Vertikal: Spalte A = Kategorie, Spalte B = Wert, mehrere Zeilen pro Lead
    """
    try:
        encodings = ['utf-8', 'utf-8-sig', 'latin-1', 'cp1252']
        content = None
        
        for encoding in encodings:
            try:
                content = file_content.decode(encoding)
                break
            except UnicodeDecodeError:
                continue
        
        if content is None:
            raise ValueError("Konnte CSV-Datei nicht dekodieren")
        
        # Erkenne Trennzeichen
        delimiter = detect_delimiter(content)
        
        # Prüfe ob vertikales Format (Kategorie, Wert)
        lines = content.strip().split('\n')
        if len(lines) < 2:
            raise ValueError("CSV-Datei enthält nicht genug Zeilen")
        
        # Prüfe ob vertikales Format
        # Vertikales Format: Spalte A enthält Kategorien (wie "Anbieter_Name", "Postleitzahl", etc.)
        # Prüfe erste paar Zeilen, ob sie bekannte Kategorien enthalten
        is_vertical = False
        category_keywords = ['anbieter', 'postleitzahl', 'plz', 'ort', 'stadt', 'grundstücksfläche', 
                           'grundstuecksflaeche', 'wohnfläche', 'wohnflaeche', 'preis', 'preis (€)', 'preis (euro)', 
                           'telefon', 'tel', 'features', 'ausstattung', 'makler', 'immobilien_typ', 'immobilientyp',
                           'baujahr', 'lage', 'lagebeschreibung']
        
        # Prüfe erste 10 Zeilen (erweitert für bessere Erkennung)
        for i, line in enumerate(lines[:10]):
            if not line.strip():
                continue
            # Verwende csv.reader für korrektes Parsing (behandelt Anführungszeichen)
            try:
                import csv as csv_module
                reader = csv_module.reader([line], delimiter=delimiter)
                parts = next(reader)
                if len(parts) >= 2:
                    first_col = parts[0].strip().lower()
                    # Wenn erste Spalte eine bekannte Kategorie enthält
                    if any(keyword in first_col for keyword in category_keywords):
                        is_vertical = True
                        print(f"[DEBUG CSV] Vertikales Format erkannt in Zeile {i+1}: '{first_col}'")
                        break
            except:
                # Fallback: Einfaches Split
                parts = line.split(delimiter)
                if len(parts) >= 2:
                    first_col = parts[0].strip().lower()
                    if any(keyword in first_col for keyword in category_keywords):
                        is_vertical = True
                        print(f"[DEBUG CSV] Vertikales Format erkannt in Zeile {i+1}: '{first_col}'")
                        break
        
        # Zusätzlich: Prüfe ob Header "Kategorie,Wert" vorhanden
        first_line = lines[0].strip().lower() if lines else ''
        delimiter_escaped = delimiter.replace(';', r'\;').replace(',', ',')
        if first_line in [f'kategorie{delimiter}wert', 'kategorie,wert', 'kategorie;wert', 'category,value', 'category;value'] or \
           (delimiter in first_line and len(first_line.split(delimiter)) == 2 and 
            ('kategorie' in first_line.lower() or 'category' in first_line.lower())):
            is_vertical = True
            print(f"[DEBUG CSV] Vertikales Format erkannt durch Header: '{first_line}'")
        
        print(f"[DEBUG CSV] Format-Erkennung: is_vertical = {is_vertical}, delimiter = '{delimiter}'")
        
        if is_vertical:
            # Vertikales Format: Spalte A = Kategorie, Spalte B = Wert
            return parse_vertical_format(content, delimiter)
        else:
            # Horizontales Format: Standard CSV
            csv_reader = csv.DictReader(io.StringIO(content), delimiter=delimiter)
            rows = list(csv_reader)
            
            if not rows:
                raise ValueError("CSV-Datei ist leer")
            
            return rows
    except Exception as e:
        raise ValueError(f"Fehler beim Parsen der CSV-Datei: {str(e)}")


def parse_vertical_format(content: str, delimiter: str = ',') -> List[dict]:
    """Parst vertikales Format: Kategorie, Wert - mehrere Zeilen pro Lead."""
    csv_reader = csv.reader(io.StringIO(content), delimiter=delimiter)
    rows = list(csv_reader)
    
    if len(rows) < 2:
        raise ValueError("CSV-Datei enthält nicht genug Zeilen")
    
    # Überspringe Header-Zeile falls vorhanden
    if rows[0][0].lower() in ['kategorie', 'category']:
        rows = rows[1:]
    
    leads = []
    current_lead = {}
    
    # Mögliche Kategorien (case-insensitive, auch abgeschnittene Namen)
    # Prüft ob der Kategoriename mit bekannten Begriffen beginnt
    def map_category(category: str) -> Optional[str]:
        """Mappt einen Kategorienamen (auch abgeschnitten) zu einem Standard-Namen."""
        cat_lower = category.lower().strip()
        
        # Exakte Treffer
        exact_mapping = {
            'anbieter_name': 'anbieter_name',
            'anbieter': 'anbieter_name',
            'name': 'anbieter_name',
            'postleitzahl': 'postleitzahl',
            'plz': 'postleitzahl',
            'ort': 'ort',
            'stadt': 'ort',
            'wohnort': 'ort',
            'grundstücksfläche': 'grundstuecksflaeche',
            'grundstuecksflaeche': 'grundstuecksflaeche',
            'grundstücksflaeche': 'grundstuecksflaeche',
            'wohnfläche': 'wohnflaeche',
            'wohnflaeche': 'wohnflaeche',
            'preis': 'preis',
            'preis (€)': 'preis',
            'preis (euro)': 'preis',
            'preis €': 'preis',
            'telefonnummer': 'telefonnummer',
            'telefon': 'telefonnummer',
            'tel': 'telefonnummer',
            'handy': 'telefonnummer',
            'features': 'features',
            'ausstattung': 'features',
            'merkmale': 'features',
            'eigenschaften': 'features',
            'immobilien_typ': 'immobilien_typ',
            'immobilientyp': 'immobilien_typ',
            'immobilien typ': 'immobilien_typ',
            'typ': 'immobilien_typ',
            'baujahr': 'baujahr',
            'baujahr (jjjj)': 'baujahr',
            'lage': 'lage',
            'lagebeschreibung': 'lage',
            'makler_id': 'makler_id',
            'makler_name': 'makler_name',
            'makler_email': 'makler_email',
            'makler': 'makler_name'
        }
        
        if cat_lower in exact_mapping:
            return exact_mapping[cat_lower]
        
        # Prüfe auf Teilübereinstimmungen (für abgeschnittene Namen und Tippfehler)
        # Anbieter_Name: Erkennt auch "Anbieter_Nlame", "Anbieter" etc.
        if 'anbieter' in cat_lower or (cat_lower.startswith('name') and len(cat_lower) > 3):
            return 'anbieter_name'
        # Postleitzahl / PLZ
        if cat_lower.startswith('postleitzahl') or cat_lower.startswith('plz') or 'plz' in cat_lower:
            return 'postleitzahl'
        # Ort / Stadt
        if cat_lower in ['ort', 'stadt', 'wohnort'] or cat_lower.startswith('ort') or cat_lower.startswith('stadt'):
            return 'ort'
        # Grundstücksfläche: Erkennt auch "Grundstücksf", "Grundstücksfl" etc.
        if 'grundstücks' in cat_lower or 'grundstuecks' in cat_lower or cat_lower.startswith('grundstücks') or cat_lower.startswith('grundstuecks'):
            return 'grundstuecksflaeche'
        # Wohnfläche: Erkennt auch "Wohnfl", "Wohnflä" etc.
        if 'wohnfl' in cat_lower or cat_lower.startswith('wohnfl'):
            return 'wohnflaeche'
        # Preis
        if cat_lower.startswith('preis') or 'preis' in cat_lower:
            return 'preis'
        # Telefonnummer: Erkennt auch "Telefonnumm", "Telefonnum" etc.
        if 'telefon' in cat_lower or cat_lower.startswith('tel') or ('telefon' in cat_lower and 'num' in cat_lower):
            return 'telefonnummer'
        # Features / Ausstattung
        if cat_lower.startswith('features') or cat_lower in ['ausstattung', 'merkmale', 'eigenschaften'] or 'feature' in cat_lower:
            return 'features'
        # Immobilien Typ
        if 'immobilien' in cat_lower and ('typ' in cat_lower or 'type' in cat_lower) or cat_lower == 'typ':
            return 'immobilien_typ'
        # Baujahr
        if cat_lower.startswith('baujahr') or cat_lower == 'baujahr' or ('bau' in cat_lower and 'jahr' in cat_lower):
            return 'baujahr'
        # Lage
        if cat_lower.startswith('lage') or cat_lower == 'lage' or 'lagebeschreibung' in cat_lower:
            return 'lage'
        # Makler
        if cat_lower.startswith('makler') or 'makler' in cat_lower:
            if 'id' in cat_lower:
                return 'makler_id'
            elif 'email' in cat_lower:
                return 'makler_email'
            else:
                return 'makler_name'
        
        return None
    
    for row in rows:
        if len(row) < 2:
            # Leere Zeile oder unvollständige Zeile
            if not any(row):  # Komplett leer
                if current_lead:
                    leads.append(current_lead)
                    current_lead = {}
            continue
        
        category = row[0].strip()
        value = row[1].strip() if len(row) > 1 else ''
        
        # Leere Zeile = neuer Lead
        if not category and not value:
            if current_lead:
                leads.append(current_lead)
                current_lead = {}
            continue
        
        # Mappe Kategorie
        mapped_category = map_category(category)
        if mapped_category:
            current_lead[mapped_category] = value
            # Debug für erste paar Zeilen
            if len(leads) == 0 and len(current_lead) <= 3:
                print(f"[DEBUG VERTIKAL MAP] Kategorie '{category}' -> gemappt zu '{mapped_category}' = '{value}'")
        else:
            # Unbekannte Kategorie - speichere trotzdem mit Original-Namen
            current_lead[category.lower()] = value
            if len(leads) == 0 and len(current_lead) <= 3:
                print(f"[DEBUG VERTIKAL MAP] Kategorie '{category}' -> NICHT gemappt, speichere als '{category.lower()}' = '{value}'")
    
    # Füge letzten Lead hinzu
    if current_lead:
        leads.append(current_lead)
    
    if not leads:
        raise ValueError("Keine Leads in vertikalem Format gefunden")
    
    return leads


def find_makler_by_identifier(db: Session, identifier: str) -> Optional[Makler]:
    """Findet einen Makler anhand von ID, Firmenname oder Email."""
    try:
        makler_id = int(identifier.strip())
        makler = db.query(Makler).filter(Makler.id == makler_id).first()
        if makler:
            return makler
    except ValueError:
        pass
    
    makler = db.query(Makler).filter(Makler.firmenname.ilike(f"%{identifier.strip()}%")).first()
    if makler:
        return makler
    
    makler = db.query(Makler).filter(Makler.email.ilike(identifier.strip())).first()
    if makler:
        return makler
    
    return None


def find_makler_by_postleitzahl(db: Session, postleitzahl: str) -> List[int]:
    """
    Findet alle Makler, die für die gegebene Postleitzahl zuständig sind.
    Gibt eine Liste von Makler-IDs zurück.
    """
    if not postleitzahl or not postleitzahl.strip():
        return []
    
    plz = postleitzahl.strip()
    
    # Hole alle Makler mit Gebiet-Informationen
    makler = db.query(Makler).filter(Makler.gebiet.isnot(None)).all()
    
    matching_makler_ids = []
    
    for m in makler:
        if not m.gebiet:
            continue
        
        # Parse Gebiet: Kommagetrennte Liste von PLZ (z.B. "10115, 10117, 10119")
        gebiet_plz = [p.strip() for p in m.gebiet.split(',')]
        
        # Prüfe ob die PLZ des Leads in der Gebiet-Liste ist
        if plz in gebiet_plz:
            matching_makler_ids.append(m.id)
    
    return matching_makler_ids


def parse_float(value: str) -> Optional[float]:
    """Konvertiert einen String zu einem Float. Unterstützt deutsches Format (150.000,00 €)."""
    if not value:
        return None
    
    try:
        # Konvertiere zu String und entferne Leerzeichen
        s = str(value).strip()
        if not s:
            return None
        
        # Entferne Euro-Symbol (€) und andere Symbole
        s = s.replace('€', '').replace('EUR', '').replace('Euro', '')
        s = s.strip()
        
        # Entferne alle Leerzeichen
        s = s.replace(' ', '')
        
        # DEUTSCHES FORMAT: "150.000,00" oder "150000,00"
        # Regel: Wenn Punkt UND Komma vorhanden → Punkt = Tausender, Komma = Dezimal
        if '.' in s and ',' in s:
            # Entferne alle Punkte (Tausender-Trenner), ersetze Komma durch Punkt
            s = s.replace('.', '').replace(',', '.')
        # NUR KOMMA: "150000,50" → Komma = Dezimal
        elif ',' in s:
            s = s.replace(',', '.')
        # NUR PUNKT: "150000.50" → Punkt = Dezimal (US-Format)
        # Oder mehrere Punkte: "150.000.00" → alle Punkte entfernen (fehlerhaftes Format)
        elif '.' in s:
            parts = s.split('.')
            if len(parts) == 2:
                # Ein Punkt = Dezimaltrennzeichen
                pass  # Bereits korrekt
            else:
                # Mehrere Punkte = alle entfernen (fehlerhaftes Format)
                s = s.replace('.', '')
        
        # Konvertiere zu Float
        return float(s)
    except (ValueError, AttributeError, TypeError):
        return None


def _generate_unique_lead_nummer(db: Session, used_numbers: set) -> int:
    """
    Generiert eine eindeutige, zufällige Lead-Nummer.
    """
    max_attempts = 1000
    # Hole alle existierenden Nummern aus DB (falls noch nicht im Set)
    existing_in_db = set(db.query(Lead.lead_nummer).filter(Lead.lead_nummer.isnot(None)).all())
    existing_in_db = {num[0] for num in existing_in_db}
    all_existing = used_numbers.union(existing_in_db)
    
    # Versuche 5-stellige Nummer
    for _ in range(max_attempts):
        nummer = random.randint(10000, 99999)
        if nummer not in all_existing:
            return nummer
    
    # Fallback: 6-stellige Nummer
    for _ in range(max_attempts):
        nummer = random.randint(100000, 999999)
        if nummer not in all_existing:
            return nummer
    
    # Letzter Fallback: Timestamp-basiert
    nummer = int(time.time() * 100) % 1000000
    while nummer in all_existing:
        nummer = (nummer + 1) % 1000000
    return nummer


@router.post("/upload/import-leads")
async def import_leads_from_csv(
    file: UploadFile = File(...),
    makler_id: Optional[int] = Form(None),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Importiert Leads aus einer CSV-Datei.
    Erlaubt für: Manager, Telefonist, Uploader, Admin
    """
    # Prüfe Berechtigung: Uploader, Manager, Telefonist, Admin dürfen importieren
    if current_user.role not in [UserRole.UPLOADER, UserRole.MANAGER, UserRole.TELEFONIST, UserRole.ADMIN]:
        raise HTTPException(
            status_code=403,
            detail="Zugriff verweigert. Sie haben keine Berechtigung zum Importieren von Leads."
        )
    """
    Importiert Leads aus einer CSV-Datei.
    
    Erwartetes CSV-Format:
    - Spalten: Anbieter_Name, Postleitzahl, Ort, Grundstücksfläche, Wohnfläche, Telefonnummer, Features
    - Optional: Makler_ID oder Makler_Name (falls nicht über Parameter angegeben)
    - Features können kommagetrennt sein (z.B. "Keller, Balkon, Garten")
    """
    if not file.filename or not file.filename.endswith('.csv'):
        raise HTTPException(status_code=400, detail="Nur CSV-Dateien werden unterstützt")
    
    file_content = await file.read()
    
    try:
        rows = parse_csv_file(file_content)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    
    expected_columns = {
        'anbieter_name': ['anbieter_name', 'anbieter', 'name', 'anbieter name'],
        'postleitzahl': ['postleitzahl', 'plz', 'postleitzahl'],
        'ort': ['ort', 'stadt', 'wohnort'],
        'grundstuecksflaeche': ['grundstücksfläche', 'grundstuecksflaeche', 'grundstücksflaeche', 'grundstücksfläche (m²)', 'grundstücksfläche m²'],
        'wohnflaeche': ['wohnfläche', 'wohnflaeche', 'wohnfläche (m²)', 'wohnfläche m²'],
        'preis': ['preis', 'preis (€)', 'preis (euro)', 'preis €', 'preis in euro', 'preis in €'],
        'telefonnummer': ['telefonnummer', 'telefon', 'tel', 'handy'],
        'features': ['features', 'ausstattung', 'merkmale', 'eigenschaften'],
        'immobilien_typ': ['immobilien_typ', 'immobilientyp', 'immobilien typ', 'typ'],
        'baujahr': ['baujahr', 'baujahr (jjjj)'],
        'lage': ['lage', 'lagebeschreibung']
    }
    
    if not rows:
        raise HTTPException(status_code=400, detail="CSV-Datei enthält keine Daten")
    
    # Prüfe ob vertikales Format (Keys sind bereits gemappte Kategorien)
    is_vertical_format = False
    if rows and isinstance(rows[0], dict):
        # Im vertikalen Format sind die Keys bereits die gemappten Kategorien
        first_row_keys = [k.lower() for k in rows[0].keys()]
        is_vertical_format = any(k in ['makler_id', 'makler_name', 'makler_email', 'anbieter_name'] for k in first_row_keys)
    
    if is_vertical_format:
        # Vertikales Format: Keys sind bereits Kategorien
        csv_headers = list(rows[0].keys()) if rows else []
        column_mapping = {}
        # Im vertikalen Format sind die Keys bereits die Kategorien
        for row in rows:
            for key in row.keys():
                key_lower = key.lower()
                if key_lower in ['anbieter_name', 'anbieter', 'name']:
                    column_mapping['anbieter_name'] = key
                elif key_lower in ['postleitzahl', 'plz']:
                    column_mapping['postleitzahl'] = key
                elif key_lower in ['ort', 'stadt', 'wohnort']:
                    column_mapping['ort'] = key
                elif 'grundstücksfläche' in key_lower or 'grundstuecksflaeche' in key_lower:
                    column_mapping['grundstuecksflaeche'] = key
                elif 'wohnfläche' in key_lower or 'wohnflaeche' in key_lower:
                    column_mapping['wohnflaeche'] = key
                elif key_lower.startswith('preis') or 'preis' in key_lower:
                    column_mapping['preis'] = key
                    print(f"[DEBUG VERTIKAL] Preis-Spalte gefunden: '{key}' -> Mapping gesetzt")
                elif key_lower in ['telefonnummer', 'telefon', 'tel', 'handy']:
                    column_mapping['telefonnummer'] = key
                elif key_lower in ['features', 'ausstattung', 'merkmale', 'eigenschaften']:
                    column_mapping['features'] = key
                elif key_lower in ['immobilien_typ', 'immobilientyp', 'immobilien typ', 'typ']:
                    column_mapping['immobilien_typ'] = key
                elif key_lower.startswith('baujahr') or ('bau' in key_lower and 'jahr' in key_lower):
                    column_mapping['baujahr'] = key
                elif key_lower.startswith('lage') or 'lagebeschreibung' in key_lower:
                    column_mapping['lage'] = key
        
        print(f"[DEBUG VERTIKAL] Column Mapping: {column_mapping}")
        if rows:
            print(f"[DEBUG VERTIKAL] Erste Zeile Keys: {list(rows[0].keys())}")
            print(f"[DEBUG VERTIKAL] Erste Zeile Werte: {rows[0]}")
        
        # Prüfe ob Makler in den Daten vorhanden
        makler_column = None
        has_makler_in_data = False
        for row in rows:
            for key in row.keys():
                key_lower = key.lower()
                if key_lower in ['makler_id', 'makler_name', 'makler_email', 'makler']:
                    makler_column = key
                    has_makler_in_data = True
                    break
            if has_makler_in_data:
                break
    else:
        # Horizontales Format: Standard CSV mit Headern
        original_headers = list(rows[0].keys())
        csv_headers_lower = [col.strip().lower() for col in original_headers]
        column_mapping = {}
        
        for field_name, possible_names in expected_columns.items():
            for idx, header_lower in enumerate(csv_headers_lower):
                # Normalisiere Vergleich: entferne Leerzeichen, Sonderzeichen
                normalized_header = header_lower.strip()
                normalized_possible = [name.lower().strip() for name in possible_names]
                if normalized_header in normalized_possible:
                    # Verwende den originalen Header-Namen (case-sensitive)
                    column_mapping[field_name] = original_headers[idx]
                    break
        
        # Spezialbehandlung für Preis (kann auch mit Varianten wie "Preis (€)" kommen)
        # Prüfe ZUERST ob bereits ein Mapping existiert
        if 'preis' not in column_mapping:
            # Suche nach "preis" in allen Headern (case-insensitive)
            for idx, header_lower in enumerate(csv_headers_lower):
                if 'preis' in header_lower:
                    column_mapping['preis'] = original_headers[idx]
                    print(f"[DEBUG CSV Import] Preis-Spalte gefunden: '{original_headers[idx]}' -> Mapping gesetzt")
                    break
        
        # Debug: Zeige finales Mapping und verfügbare Headers
        print(f"[DEBUG CSV Import] Verfügbare Headers: {original_headers}")
        print(f"[DEBUG CSV Import] Finales Column-Mapping: {column_mapping}")
        
        makler_column = None
        has_makler_in_data = False
        for idx, header_lower in enumerate(csv_headers_lower):
            if 'makler' in header_lower:
                makler_column = original_headers[idx]
                has_makler_in_data = True
                break
    
    # Makler ist optional - Leads können ohne Makler importiert werden (Status: unqualifiziert)
    # makler_id wird ignoriert - Leads werden immer ohne Makler importiert
    
    imported = []
    errors = []
    used_lead_numbers = set()  # Set zum Tracken von Nummern innerhalb dieses Imports
    
    for row_num, row in enumerate(rows, start=2):
        try:
            # Finde Makler für diese Zeile (optional)
            current_makler = None
            if makler_id:
                current_makler = db.query(Makler).filter(Makler.id == makler_id).first()
            elif makler_column:
                makler_identifier = row.get(makler_column, '').strip()
                if makler_identifier:
                    current_makler = find_makler_by_identifier(db, makler_identifier)
            else:
                # Prüfe ob Makler direkt in den Daten steht (vertikales Format)
                for key in ['makler_id', 'makler_name', 'makler_email', 'makler']:
                    if key in row and row[key]:
                        current_makler = find_makler_by_identifier(db, str(row[key]))
                        if current_makler:
                            break
            
            # Makler ist optional - wenn nicht gefunden, bleibt Lead ohne Makler (Status: unqualifiziert)
            
            anbieter_name = row.get(column_mapping.get('anbieter_name', ''), '').strip() if column_mapping.get('anbieter_name') else None
            if not anbieter_name:
                anbieter_name = None
            
            postleitzahl = row.get(column_mapping.get('postleitzahl', ''), '').strip() if column_mapping.get('postleitzahl') else None
            if not postleitzahl:
                postleitzahl = None
                
            ort = row.get(column_mapping.get('ort', ''), '').strip() if column_mapping.get('ort') else None
            if not ort:
                ort = None
                
            grundstuecksflaeche = parse_float(row.get(column_mapping.get('grundstuecksflaeche', ''), '')) if column_mapping.get('grundstuecksflaeche') else None
            wohnflaeche = parse_float(row.get(column_mapping.get('wohnflaeche', ''), '')) if column_mapping.get('wohnflaeche') else None
            
            # PREIS-EXTRAKTION - Verbessert
            preis = None
            
            # Zuerst: Versuche über column_mapping (falls vorhanden)
            if column_mapping.get('preis'):
                preis_key = column_mapping.get('preis')
                preis_raw = row.get(preis_key, '')
                if preis_raw is not None and preis_raw != '':
                    preis_str = str(preis_raw).strip()
                    if preis_str:
                        print(f"[DEBUG PREIS] Versuche Preis zu parsen aus column_mapping: '{preis_str}' (Key: '{preis_key}')")
                        preis = parse_float(preis_str)
                        print(f"[DEBUG PREIS] Ergebnis nach parse_float: {preis}")
            
            # Fallback: Suche in ALLEN Spalten nach "preis" (case-insensitive)
            if preis is None:
                for key in row.keys():
                    key_lower = str(key).lower().strip()
                    if 'preis' in key_lower:
                        preis_raw = row.get(key)
                        if preis_raw is not None and preis_raw != '':
                            preis_str = str(preis_raw).strip()
                            if preis_str:
                                print(f"[DEBUG PREIS] Versuche Preis zu parsen aus Fallback-Suche: '{preis_str}' (Key: '{key}')")
                                preis = parse_float(preis_str)
                                print(f"[DEBUG PREIS] Ergebnis nach parse_float: {preis}")
                                if preis is not None:
                                    # Preis gefunden und konvertiert
                                    break
            
            telefonnummer = row.get(column_mapping.get('telefonnummer', ''), '').strip() if column_mapping.get('telefonnummer') else None
            if not telefonnummer:
                telefonnummer = None
                
            features = row.get(column_mapping.get('features', ''), '').strip() if column_mapping.get('features') else None
            if not features:
                features = None
            
            # Immobilien Typ - IMMER am Anfang initialisieren
            immobilien_typ = None
            if is_vertical_format:
                # Im vertikalen Format sind die Keys bereits gemappte Kategorien
                immobilien_typ_raw = row.get('immobilien_typ')
                if immobilien_typ_raw is not None and str(immobilien_typ_raw).strip():
                    immobilien_typ = str(immobilien_typ_raw).strip()
                # Debug für erste Zeile
                if row_num == 2:
                    print(f"[DEBUG IMMOBILIEN_TYP] Row Keys: {list(row.keys())}")
                    print(f"[DEBUG IMMOBILIEN_TYP] Looking for 'immobilien_typ' in row: {'immobilien_typ' in row}")
                    print(f"[DEBUG IMMOBILIEN_TYP] Raw Value: {immobilien_typ_raw}, Final: {immobilien_typ}")
                    # Prüfe alle Keys, die ähnlich klingen
                    for key in row.keys():
                        if 'immobilien' in str(key).lower() or 'typ' in str(key).lower():
                            print(f"[DEBUG IMMOBILIEN_TYP] Found similar key '{key}' = '{row.get(key)}'")
            else:
                # Horizontales Format: verwende column_mapping
                if column_mapping.get('immobilien_typ'):
                    immobilien_typ_raw = row.get(column_mapping.get('immobilien_typ'))
                    if immobilien_typ_raw is not None:
                        immobilien_typ_value = str(immobilien_typ_raw).strip()
                        if immobilien_typ_value:
                            immobilien_typ = immobilien_typ_value
            
            # Baujahr
            baujahr = None
            if is_vertical_format:
                # Im vertikales Format sind die Keys bereits gemappte Kategorien
                baujahr_raw = row.get('baujahr')
                if baujahr_raw is not None:
                    baujahr_str = str(baujahr_raw).strip()
                    if baujahr_str:
                        try:
                            baujahr = int(baujahr_str)
                        except (ValueError, TypeError):
                            baujahr = None
                # Debug für erste Zeile
                if row_num == 2:
                    print(f"[DEBUG BAUJAHR] Looking for 'baujahr' in row: {'baujahr' in row}")
                    print(f"[DEBUG BAUJAHR] Raw Value: {baujahr_raw}, Final: {baujahr}")
                    # Prüfe alle Keys, die ähnlich klingen
                    for key in row.keys():
                        if 'bau' in str(key).lower() or 'jahr' in str(key).lower():
                            print(f"[DEBUG BAUJAHR] Found similar key '{key}' = '{row.get(key)}'")
            else:
                # Horizontales Format: verwende column_mapping
                if column_mapping.get('baujahr'):
                    baujahr_raw = row.get(column_mapping.get('baujahr'))
                    if baujahr_raw is not None:
                        baujahr_str = str(baujahr_raw).strip()
                        if baujahr_str:
                            try:
                                baujahr = int(baujahr_str)
                            except (ValueError, TypeError):
                                baujahr = None
            
            # Lage
            lage = None
            if is_vertical_format:
                # Im vertikalen Format sind die Keys bereits gemappte Kategorien
                lage_raw = row.get('lage')
                if lage_raw is not None and str(lage_raw).strip():
                    lage = str(lage_raw).strip()
                # Debug für erste Zeile
                if row_num == 2:
                    print(f"[DEBUG LAGE] Looking for 'lage' in row: {'lage' in row}")
                    print(f"[DEBUG LAGE] Raw Value: {lage_raw}, Final: {lage}")
                    # Prüfe alle Keys, die ähnlich klingen
                    for key in row.keys():
                        if 'lage' in str(key).lower():
                            print(f"[DEBUG LAGE] Found similar key '{key}' = '{row.get(key)}'")
            else:
                # Horizontales Format: verwende column_mapping
                if column_mapping.get('lage'):
                    lage_raw = row.get(column_mapping.get('lage'))
                    if lage_raw is not None:
                        lage_value = str(lage_raw).strip()
                        if lage_value:
                            lage = lage_value
            
            # Debug für erste Zeile (NACH Initialisierung aller Variablen)
            if row_num == 2:
                print(f"[CSV IMPORT] Row {row_num}: Preis={preis}, Column Mapping Preis: {column_mapping.get('preis')}, Verfügbare Keys: {list(row.keys())}")
                print(f"[CSV IMPORT] Row {row_num}: Vollständige Row-Daten: {row}")
                print(f"[CSV IMPORT] Row {row_num}: Immobilien_Typ={immobilien_typ}, Baujahr={baujahr}, Lage={lage}")
            
            # Finde alle Makler, die für diese Postleitzahl zuständig sind
            moegliche_makler_ids = []
            if postleitzahl:
                moegliche_makler_ids = find_makler_by_postleitzahl(db, postleitzahl)
            
            # Speichere als kommagetrennte Liste (z.B. "1, 3, 5")
            moegliche_makler_ids_str = ', '.join(map(str, moegliche_makler_ids)) if moegliche_makler_ids else None
            
            # Lead erstellen MIT PREIS
            # Debug: Zeige Werte vor Lead-Erstellung
            if row_num == 2:
                print(f"[DEBUG LEAD ERSTELLUNG] Vor Lead-Erstellung:")
                print(f"  Immobilien_Typ: {immobilien_typ} (Type: {type(immobilien_typ)})")
                print(f"  Baujahr: {baujahr} (Type: {type(baujahr)})")
                print(f"  Lage: {lage} (Type: {type(lage)})")
            
            # Generiere eindeutige zufällige Lead-Nummer
            lead_nummer = _generate_unique_lead_nummer(db, used_lead_numbers)
            used_lead_numbers.add(lead_nummer)  # Füge zur Set hinzu, damit sie nicht nochmal verwendet wird
            
            lead = Lead(
                lead_nummer=lead_nummer,
                makler_id=current_makler.id if current_makler else None,
                status=schemas.LeadStatus.UNQUALIFIZIERT.value,
                erstellt_am=datetime.utcnow(),
                created_by_user_id=current_user.id,
                anbieter_name=anbieter_name or (current_makler.firmenname if current_makler else None),
                postleitzahl=postleitzahl,
                ort=ort,
                grundstuecksflaeche=grundstuecksflaeche,
                wohnflaeche=wohnflaeche,
                preis=preis,  # PREIS WIRD HIER GESPEICHERT
                telefonnummer=telefonnummer,
                features=features,
                immobilien_typ=immobilien_typ,
                baujahr=baujahr,
                lage=lage,
                moegliche_makler_ids=moegliche_makler_ids_str
            )
            
            db.add(lead)
            db.flush()  # Flush um die ID zu bekommen
            
            # Debug: Prüfe ob neue Felder gespeichert wurden
            if row_num == 2:
                print(f"[DEBUG LEAD ERSTELLT] ID={lead.id}")
                print(f"  Immobilien_Typ: '{lead.immobilien_typ}' (Type: {type(lead.immobilien_typ)})")
                print(f"  Baujahr: {lead.baujahr} (Type: {type(lead.baujahr)})")
                print(f"  Lage: '{lead.lage}' (Type: {type(lead.lage)})")
            
            imported.append({
                'row': row_num,
                'id': lead.id,
                'makler': current_makler.firmenname if current_makler else 'Kein Makler',
                'ort': ort or 'N/A',
                'postleitzahl': postleitzahl or 'N/A',
                'preis': preis
            })
            
        except Exception as e:
            import traceback
            error_msg = f'Fehler beim Import: {str(e)}'
            print(f"[ERROR CSV IMPORT] Zeile {row_num}: {error_msg}")
            print(f"[ERROR CSV IMPORT] Traceback: {traceback.format_exc()}")
            errors.append({'row': row_num, 'error': error_msg})
    
    try:
        db.commit()
        # Debug: Prüfe ob alle Felder gespeichert wurden
        if imported and len(imported) > 0:
            first_imported_id = imported[0].get('id')
            if first_imported_id:
                first_imported_lead = db.query(Lead).filter(Lead.id == first_imported_id).first()
                if first_imported_lead:
                    print(f"[DEBUG CSV Import] Nach Commit: Lead {first_imported_lead.id}")
                    print(f"  Preis: {first_imported_lead.preis}")
                    print(f"  Immobilien_Typ: '{first_imported_lead.immobilien_typ}'")
                    print(f"  Baujahr: {first_imported_lead.baujahr}")
                    print(f"  Lage: '{first_imported_lead.lage}'")
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Fehler beim Speichern der Leads: {str(e)}")
    
    return {
        'message': f'{len(imported)} Leads erfolgreich importiert',
        'imported': len(imported),
        'errors': len(errors),
        'imported_details': imported[:10],
        'error_details': errors[:10]
    }

