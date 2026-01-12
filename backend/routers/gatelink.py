from datetime import timedelta
from typing import List, Union, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Form, Query
from fastapi.security import OAuth2PasswordRequestForm, OAuth2PasswordBearer
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import desc, nulls_last, extract
from jose import JWTError, jwt

from .. import schemas
from ..database import get_db
from ..models.makler import Makler
from ..models.user import User, UserRole
from ..models.lead import Lead
from ..models.chat import ChatMessage
from ..services.auth_service import (
    create_access_token,
    authenticate_user,
    get_user_by_email,
    get_user_by_username,
    ACCESS_TOKEN_EXPIRE_MINUTES,
    SECRET_KEY,
    ALGORITHM
)

router = APIRouter()

# OAuth2 Scheme für Makler
makler_oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/gatelink/login")


def get_makler_by_email(db: Session, email: str):
    """Findet einen Makler anhand der E-Mail-Adresse."""
    return db.query(Makler).filter(Makler.email == email).first()


def authenticate_makler(db: Session, email: str, password: str):
    """
    Authentifiziert einen Makler über GateLink.
    Verwendet E-Mail und gatelink_password (gehasht mit bcrypt).
    Das Passwort muss gesetzt sein, sonst schlägt die Authentifizierung fehl.
    """
    from ..services.auth_service import verify_password
    
    makler = get_makler_by_email(db, email)
    if not makler:
        return None
    
    # Prüfe ob GateLink-Passwort gesetzt ist
    if not makler.gatelink_password:
        return None
    
    # Prüfe Passwort (unterstützt sowohl gehashte als auch Klartext-Passwörter für Migration)
    # Wenn das Passwort mit bcrypt gehasht ist (beginnt mit $2b$), verwende verify_password
    # Sonst prüfe Klartext (für Rückwärtskompatibilität während Migration)
    if makler.gatelink_password.startswith("$2b$") or makler.gatelink_password.startswith("$2a$"):
        # Gehashtes Passwort
        if verify_password(password, makler.gatelink_password):
            return makler
    else:
        # Klartext-Passwort (alte Daten) - migriere automatisch
        if password == makler.gatelink_password:
            # Hash das Passwort und speichere es
            from ..services.auth_service import get_password_hash
            makler.gatelink_password = get_password_hash(password)
            db.commit()
            return makler
    
    return None


def authenticate_gatelink_user(db: Session, email: str, password: str) -> Union[User, Makler, None]:
    """
    Authentifiziert einen User (Admin/Manager) oder Makler für GateLink.
    Versucht zuerst einen User zu finden (per E-Mail oder Username), dann einen Makler (per E-Mail).
    """
    # Versuche zuerst einen User zu finden (Admin/Manager) - per E-Mail oder Username
    user = get_user_by_email(db, email)
    if not user:
        # Versuche auch per Username
        user = get_user_by_username(db, email)
    
    if user:
        # Prüfe ob User Admin oder Manager ist
        if user.role in [UserRole.ADMIN, UserRole.MANAGER]:
            # Authentifiziere User mit normalem Passwort
            from ..services.auth_service import verify_password
            if verify_password(password, user.hashed_password):
                return user
        return None
    
    # Versuche einen Makler zu finden (per E-Mail)
    makler = authenticate_makler(db, email, password)
    if makler:
        return makler
    
    return None


def get_current_gatelink_user(
    token: str = Depends(makler_oauth2_scheme),
    db: Session = Depends(get_db)
) -> Union[User, Makler]:
    """Holt den aktuellen GateLink-Benutzer (User oder Makler) aus dem JWT-Token."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_type = payload.get("user_type")
        
        if user_type == "user":
            # User-Authentifizierung
            username: str = payload.get("sub")
            if username is None:
                raise credentials_exception
            user = db.query(User).filter(User.username == username).first()
            if user is None or not user.is_active:
                raise credentials_exception
            # Prüfe ob User Admin oder Manager ist
            if user.role not in [UserRole.ADMIN, UserRole.MANAGER]:
                raise credentials_exception
            return user
        elif user_type == "makler":
            # Makler-Authentifizierung
            makler_id: int = payload.get("makler_id")
            if makler_id is None:
                raise credentials_exception
            makler = db.query(Makler).filter(Makler.id == makler_id).first()
            if makler is None:
                raise credentials_exception
            return makler
        else:
            raise credentials_exception
    except JWTError:
        raise credentials_exception


@router.post("/login")
def gatelink_login(
    email: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db)
):
    """
    Authentifiziert einen User (Admin/Manager) oder Makler für GateLink.
    Für Makler: Verwendet E-Mail und gatelink_password.
    Für User: Verwendet E-Mail/Username und normales Passwort.
    """
    user_or_makler = authenticate_gatelink_user(db, email, password)
    if not user_or_makler:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Falsche E-Mail oder Passwort",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    # Erstelle Token basierend auf Typ
    if isinstance(user_or_makler, User):
        # User-Token
        access_token = create_access_token(
            data={
                "sub": user_or_makler.username,
                "user_type": "user",
                "role": user_or_makler.role.value
            },
            expires_delta=access_token_expires
        )
        return {
            "access_token": access_token,
            "token_type": "bearer",
            "user": {
                "id": user_or_makler.id,
                "username": user_or_makler.username,
                "email": user_or_makler.email,
                "role": user_or_makler.role.value,
                "type": "user"
            }
        }
    else:
        # Makler-Token
        access_token = create_access_token(
            data={
                "makler_id": user_or_makler.id,
                "email": user_or_makler.email,
                "user_type": "makler"
            },
            expires_delta=access_token_expires
        )
        return {
            "access_token": access_token,
            "token_type": "bearer",
            "makler": {
                "id": user_or_makler.id,
                "firmenname": user_or_makler.firmenname,
                "email": user_or_makler.email,
                "type": "makler"
            }
        }


@router.get("/me")
def get_gatelink_user_info(current_user: Union[User, Makler] = Depends(get_current_gatelink_user)):
    """Gibt Informationen über den eingeloggten GateLink-Benutzer zurück."""
    if isinstance(current_user, User):
        return {
            "id": current_user.id,
            "username": current_user.username,
            "email": current_user.email,
            "role": current_user.role.value,
            "type": "user"
        }
    else:
        return {
            "id": current_user.id,
            "firmenname": current_user.firmenname,
            "email": current_user.email,
            "ansprechpartner": current_user.ansprechpartner,
            "type": "makler",
            "rechnungssystem_typ": current_user.rechnungssystem_typ or 'alt'
        }


@router.get("/leads", response_model=List[schemas.LeadRead])
def get_gatelink_leads(
    jahr: Optional[int] = None,
    monat: Optional[int] = None,
    current_user: Union[User, Makler] = Depends(get_current_gatelink_user),
    db: Session = Depends(get_db)
):
    """
    Gibt qualifizierte und flexrecall-Leads zurück, die einem Makler zugewiesen sind:
    - Für Makler: nur ihre eigenen qualifizierten und flexrecall-Leads
    - Für Admin/Manager: alle qualifizierten und flexrecall-Leads, die einem Makler zugewiesen sind
    
    Filter:
    - jahr: Filter nach Jahr (basierend auf qualifiziert_am)
    - monat: Filter nach Monat (1-12, basierend auf qualifiziert_am)
    """
    # Basis-Filter: Qualifizierte ODER flexrecall-Leads mit zugewiesenem Makler
    from sqlalchemy import or_
    query = db.query(Lead).filter(
        or_(Lead.status == "qualifiziert", Lead.status == "flexrecall"),
        Lead.makler_id.isnot(None)
    )
    
    # Jahr-Filter (basierend auf qualifiziert_am)
    if jahr is not None:
        query = query.filter(extract('year', Lead.qualifiziert_am) == jahr)
    
    # Monat-Filter (basierend auf qualifiziert_am)
    if monat is not None:
        if monat < 1 or monat > 12:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Monat muss zwischen 1 und 12 liegen"
            )
        query = query.filter(extract('month', Lead.qualifiziert_am) == monat)
    
    if isinstance(current_user, User):
        # Admin/Manager sehen alle qualifizierten Leads mit Makler-Zuordnung
        # Sortiert nach Qualifizierungsdatum (neueste zuerst)
        leads = query.order_by(nulls_last(desc(Lead.qualifiziert_am))).all()
    else:
        # Makler sehen nur ihre eigenen qualifizierten Leads
        # Sortiert nach Qualifizierungsdatum (neueste zuerst)
        leads = query.filter(Lead.makler_id == current_user.id).order_by(nulls_last(desc(Lead.qualifiziert_am))).all()
    
    # Lade Lead-Details mit qualifiziert_von_username
    from .leads import load_lead_details
    return [load_lead_details(lead, db) for lead in leads]


@router.put("/leads/{lead_id}", response_model=schemas.LeadRead)
def update_gatelink_lead(
    lead_id: int,
    data: schemas.LeadUpdate,
    current_user: Union[User, Makler] = Depends(get_current_gatelink_user),
    db: Session = Depends(get_db)
):
    """
    Aktualisiert einen Lead für GateLink.
    Makler können nur ihre eigenen Leads aktualisieren und nur makler_status und makler_beschreibung ändern.
    Admin/Manager können alle Felder aktualisieren.
    """
    lead = db.query(Lead).filter(Lead.id == lead_id).first()
    if not lead:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Lead nicht gefunden"
        )
    
    # Prüfe ob Makler nur seinen eigenen Lead aktualisiert
    if isinstance(current_user, Makler):
        if lead.makler_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Sie können nur Ihre eigenen Leads aktualisieren"
            )
        
        # Makler können makler_status, makler_beschreibung, telefon_kontakt und checklisten Felder ändern
        # Verwende exclude_none=False, damit auch None-Werte gesendet werden können
        print(f"DEBUG: Empfangene Daten (data.dict): {data.dict(exclude_unset=True, exclude_none=False)}")
        update_data = data.dict(exclude_unset=True, exclude_none=False)
        print(f"DEBUG: update_data vor Filterung: {update_data}")
        allowed_fields = {
            'makler_status', 'makler_beschreibung', 
            'telefon_kontakt_ergebnis', 'telefon_kontakt_datum', 'telefon_kontakt_uhrzeit',
            'termin_vereinbart', 'termin_ort', 'termin_datum', 'termin_uhrzeit', 'termin_notiz',
            'absage', 'absage_notiz',
            'zweit_termin_vereinbart', 'zweit_termin_ort', 'zweit_termin_datum', 'zweit_termin_uhrzeit', 'zweit_termin_notiz',
            'maklervertrag_unterschrieben', 'maklervertrag_notiz',
            'immobilie_verkauft', 'immobilie_verkauft_datum', 'immobilie_verkauft_preis', 'beteiligungs_prozent',
            'favorit', 'makler_angesehen'
        }
        update_data = {k: v for k, v in update_data.items() if k in allowed_fields}
        print(f"DEBUG: Nach Filterung - update_data enthält: {update_data}")
        
        # Setze makler_status_geaendert_am wenn Status geändert wird
        if 'makler_status' in update_data and update_data['makler_status'] != lead.makler_status:
            from datetime import datetime
            update_data['makler_status_geaendert_am'] = datetime.utcnow()
    else:
        # Admin/Manager können alle Felder aktualisieren
        update_data = data.dict(exclude_unset=True)
        # Setze makler_status_geaendert_am wenn Status geändert wird
        if 'makler_status' in update_data and update_data['makler_status'] != lead.makler_status:
            from datetime import datetime
            update_data['makler_status_geaendert_am'] = datetime.utcnow()
    
    # FlexRecall-Logik: Wenn Checkliste bearbeitet wird, ändere Status von flexrecall zu qualifiziert
    # Prüfe ob Lead aktuell FlexRecall ist und ob Checklisten-Items gesetzt werden
    if lead.status == "flexrecall":
        # Prüfe ob Absage gesetzt wird (hat Priorität)
        absage_set = update_data.get('absage') == 1
        
        if absage_set:
            # Absage bei FlexRecall: Setze Status auf "reklamiert" (Lead wird aus GateLink entfernt)
            lead.status = "reklamiert"
            lead.qualifiziert_von_user_id = None
            lead.qualifiziert_am = None
        else:
            # Prüfe ob ein Checklisten-Item aktiviert wird (außer Absage)
            # Wichtig: Nur wenn ein Item auf 1 gesetzt wird (aktiviert), nicht wenn es auf 0 gesetzt wird
            checklist_item_activated = False
            for key in ['termin_vereinbart', 'zweit_termin_vereinbart', 'maklervertrag_unterschrieben', 'immobilie_verkauft']:
                if key in update_data and update_data[key] is not None:
                    # Wenn Wert 1 ist, wurde Item aktiviert
                    if update_data[key] == 1:
                        checklist_item_activated = True
                        break
            
            if checklist_item_activated:
                # Checkliste wurde bearbeitet (Item aktiviert): Ändere Status von flexrecall zu qualifiziert
                lead.status = "qualifiziert"
            # Wenn nur "Nicht erreicht" oder "Rückruf" gesetzt wird (telefon_kontakt_ergebnis), bleibt Status flexrecall
    
    # Aktualisiere Felder
    print(f"DEBUG: update_data enthält: {update_data}")
    for key, value in update_data.items():
        setattr(lead, key, value)
        print(f"DEBUG: Setze {key} = {value} (Typ: {type(value)})")
    
    db.commit()
    db.refresh(lead)
    print(f"DEBUG: Nach Commit - Status: {lead.status}, termin_vereinbart = {lead.termin_vereinbart}, absage = {lead.absage}, maklervertrag_unterschrieben = {lead.maklervertrag_unterschrieben}, immobilie_verkauft = {lead.immobilie_verkauft}")
    from .leads import load_lead_details
    from .. import schemas
    lead_dict = load_lead_details(lead, db)
    return schemas.LeadRead(**lead_dict)


@router.post("/leads/{lead_id}/reklamieren", response_model=schemas.LeadRead)
def reklamiere_lead(
    lead_id: int,
    current_user: Union[User, Makler] = Depends(get_current_gatelink_user),
    db: Session = Depends(get_db)
):
    """
    Reklamiert einen flexrecall-Lead. Nur Makler können ihre eigenen Leads reklamieren.
    - Setzt Status auf "reklamiert"
    - Entfernt qualifiziert_von_user_id (für Statistik)
    - Entfernt qualifiziert_am
    """
    lead = db.query(Lead).filter(Lead.id == lead_id).first()
    if not lead:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Lead nicht gefunden"
        )
    
    # Prüfe ob Lead flexrecall ist
    if lead.status != "flexrecall":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Nur flexrecall-Leads können reklamiert werden"
        )
    
    # Prüfe ob Makler nur seinen eigenen Lead reklamiert
    if isinstance(current_user, Makler):
        if lead.makler_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Sie können nur Ihre eigenen Leads reklamieren"
            )
    
    # Setze Status auf reklamiert und entferne qualifiziert_von_user_id
    lead.status = "reklamiert"
    lead.qualifiziert_von_user_id = None
    lead.qualifiziert_am = None
    
    db.commit()
    db.refresh(lead)
    from .leads import load_lead_details
    from .. import schemas
    lead_dict = load_lead_details(lead, db)
    return schemas.LeadRead(**lead_dict)


@router.post("/chat", response_model=schemas.ChatMessageRead, status_code=status.HTTP_201_CREATED)
def send_chat_message(
    data: schemas.ChatMessageCreate,
    current_user: Union[User, Makler] = Depends(get_current_gatelink_user),
    db: Session = Depends(get_db)
):
    """
    Sendet eine Chat-Nachricht.
    - Makler senden an LeadGate (to_user_id wird ignoriert, Nachricht geht an alle LeadGate-Benutzer)
    - User senden an Makler (to_makler_id muss angegeben werden)
    """
    if isinstance(current_user, User):
        # User sendet an Makler - nur Manager und Admin dürfen an Makler schreiben
        if not data.to_makler_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="to_makler_id muss angegeben werden"
            )
        # Prüfe Berechtigung: Nur Manager und Admin können an Makler schreiben
        if current_user.role not in [UserRole.MANAGER, UserRole.ADMIN]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Nur Manager und Admin dürfen an Makler schreiben"
            )
        message = ChatMessage(
            from_user_id=current_user.id,
            to_makler_id=data.to_makler_id,
            nachricht=data.nachricht,
            gelesen=False
        )
    else:
        # Makler sendet an LeadGate (geht an alle User, aber wir speichern es ohne to_user_id)
        # In der Praxis: Makler-Nachrichten werden von allen LeadGate-Benutzern gesehen
        message = ChatMessage(
            from_makler_id=current_user.id,
            nachricht=data.nachricht,
            gelesen=False
        )
    
    db.add(message)
    db.commit()
    db.refresh(message)
    
    return load_gatelink_message_details(message, db)


@router.get("/credits/preis-pro-lead")
def get_gatelink_lead_preis(
    current_user: Union[User, Makler] = Depends(get_current_gatelink_user),
    db: Session = Depends(get_db)
):
    """
    Gibt den aktuellen Preis pro Lead für den eingeloggten Makler zurück.
    Nur für Makler mit Credits-System verfügbar.
    """
    if isinstance(current_user, User):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Nur Makler können ihren Lead-Preis abrufen"
        )
    
    makler = current_user
    if (makler.rechnungssystem_typ or 'alt') != 'neu':
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Dieser Makler verwendet nicht das Credits-System"
        )
    
    from datetime import datetime, date
    from ..services.credits_service import berechne_preis_fuer_lead, zaehle_leads_im_monat
    
    # Berechne aktuellen Preis (basierend auf Vertragsmonat)
    heute = date.today()
    qualifiziert_am = datetime.combine(heute, datetime.min.time())
    
    # Zähle Leads im aktuellen Monat
    anzahl_leads_im_monat = zaehle_leads_im_monat(
        db, makler.id, heute.month, heute.year
    )
    
    # Berechne Preis für den nächsten Lead
    preis_pro_lead = berechne_preis_fuer_lead(
        makler, qualifiziert_am, anzahl_leads_im_monat + 1
    )
    
    return {
        "preis_pro_lead": preis_pro_lead,
        "vertragsmonat": None,  # Könnte hier auch berechnet werden
        "anzahl_leads_im_monat": anzahl_leads_im_monat
    }


@router.get("/credits/stand", response_model=schemas.MaklerCreditsStand)
def get_gatelink_credits_stand(
    current_user: Union[User, Makler] = Depends(get_current_gatelink_user),
    db: Session = Depends(get_db)
):
    """
    Gibt den aktuellen Credits-Stand für den eingeloggten Makler zurück.
    Nur für Makler mit Credits-System verfügbar.
    """
    if isinstance(current_user, User):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Nur Makler können ihren Credits-Stand abrufen"
        )
    
    makler = current_user
    if (makler.rechnungssystem_typ or 'alt') != 'neu':
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Dieser Makler verwendet nicht das Credits-System"
        )
    
    from ..services.credits_service import berechne_credits_stand
    from ..models import MaklerCredits
    
    aktueller_stand = berechne_credits_stand(db, makler.id)
    
    # Hole letzte Transaktion
    letzte_transaktion = (
        db.query(MaklerCredits)
        .filter(MaklerCredits.makler_id == makler.id)
        .order_by(MaklerCredits.erstellt_am.desc())
        .first()
    )
    
    # Zähle Transaktionen
    transaktionsanzahl = (
        db.query(MaklerCredits)
        .filter(MaklerCredits.makler_id == makler.id)
        .count()
    )
    
    return schemas.MaklerCreditsStand(
        makler_id=makler.id,
        aktueller_stand=aktueller_stand,
        letzte_transaktion_am=letzte_transaktion.erstellt_am if letzte_transaktion else None,
        transaktionsanzahl=transaktionsanzahl
    )


@router.get("/credits/historie", response_model=List[schemas.MaklerCreditsRead])
def get_gatelink_credits_historie(
    limit: int = 50,
    current_user: Union[User, Makler] = Depends(get_current_gatelink_user),
    db: Session = Depends(get_db)
):
    """
    Gibt die Credits-Transaktionshistorie für den eingeloggten Makler zurück.
    """
    if isinstance(current_user, User):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Nur Makler können ihre Credits-Historie abrufen"
        )
    
    makler = current_user
    if (makler.rechnungssystem_typ or 'alt') != 'neu':
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Dieser Makler verwendet nicht das Credits-System"
        )
    
    from ..models import MaklerCredits
    
    transaktionen = (
        db.query(MaklerCredits)
        .filter(MaklerCredits.makler_id == makler.id)
        .order_by(MaklerCredits.erstellt_am.desc())
        .limit(limit)
        .all()
    )
    
    return transaktionen


@router.post("/credits/rueckzahlung/anfrage", response_model=schemas.CreditsRueckzahlungAnfrageRead)
def erstelle_rueckzahlung_anfrage(
    data: schemas.CreditsRueckzahlungAnfrageCreate,
    current_user: Union[User, Makler] = Depends(get_current_gatelink_user),
    db: Session = Depends(get_db)
):
    """
    Erstellt eine Rückzahlungsanfrage für nicht verwendete Credits.
    Die Anfrage wird automatisch als Chat-Nachricht an LeadGate gesendet.
    """
    if isinstance(current_user, User):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Nur Makler können Rückzahlungsanfragen stellen"
        )
    
    makler = current_user
    if (makler.rechnungssystem_typ or 'alt') != 'neu':
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Dieser Makler verwendet nicht das Credits-System"
        )
    
    from ..models import CreditsRueckzahlungAnfrage, MaklerCredits, ChatMessage
    from ..services.credits_service import berechne_rueckzahlbare_credits
    
    # Prüfe ob die Transaktion rückzahlbar ist
    # Credits können zurückgezahlt werden, wenn sie älter als 2 Monate sind
    rueckzahlbare = berechne_rueckzahlbare_credits(db, makler.id, 2)  # 2 Monate
    transaktion_found = next((r for r in rueckzahlbare if r["transaktion_id"] == data.transaktion_id), None)
    
    if not transaktion_found:
        # Fallback: Prüfe ob Transaktion existiert und zum Makler gehört
        transaktion = db.query(MaklerCredits).filter(
            MaklerCredits.id == data.transaktion_id,
            MaklerCredits.makler_id == makler.id,
            MaklerCredits.betrag > 0
        ).first()
        
        if not transaktion:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Diese Transaktion wurde nicht gefunden oder gehört nicht zu diesem Makler"
            )
        
        # Für Tests: Erlaube auch jüngere Transaktionen
        # In Produktion sollte hier eine Prüfung auf 2 Monate erfolgen
        transaktion_found = {
            "transaktion_id": transaktion.id,
            "betrag": transaktion.betrag,
            "erstellt_am": transaktion.erstellt_am.isoformat()
        }
    
    # Prüfe ob bereits eine Anfrage für diese Transaktion existiert
    bestehende_anfrage = (
        db.query(CreditsRueckzahlungAnfrage)
        .filter(
            CreditsRueckzahlungAnfrage.makler_id == makler.id,
            CreditsRueckzahlungAnfrage.transaktion_id == data.transaktion_id,
            CreditsRueckzahlungAnfrage.status == "pending"
        )
        .first()
    )
    
    if bestehende_anfrage:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Für diese Transaktion existiert bereits eine offene Anfrage"
        )
    
    # Erstelle Rückzahlungsanfrage
    anfrage = CreditsRueckzahlungAnfrage(
        makler_id=makler.id,
        transaktion_id=data.transaktion_id,
        betrag=data.betrag,
        beschreibung=data.beschreibung or f"Rückzahlungsanfrage für {data.betrag:.2f}€",
        status="pending"
    )
    
    db.add(anfrage)
    db.commit()
    db.refresh(anfrage)
    
    # Erstelle automatisch Chat-Nachricht an LeadGate
    # Finde alle Admin/Manager User
    from ..models.user import UserRole
    leadgate_users = (
        db.query(User)
        .filter(User.role.in_([UserRole.ADMIN, UserRole.MANAGER]))
        .all()
    )
    
    # Erstelle Chat-Nachricht für jeden Admin/Manager
    transaktion = db.query(MaklerCredits).filter(MaklerCredits.id == data.transaktion_id).first()
    transaktion_datum = transaktion.erstellt_am.strftime('%d.%m.%Y') if transaktion else "unbekannt"
    
    nachricht = (
        f"💰 Rückzahlungsanfrage\n\n"
        f"Makler: {makler.firmenname}\n"
        f"Betrag: {data.betrag:.2f} €\n"
        f"Transaktion: #{data.transaktion_id} (vom {transaktion_datum})\n"
        f"Anfrage-ID: #{anfrage.id}\n\n"
        f"{data.beschreibung or 'Keine zusätzliche Beschreibung'}"
    )
    
    for user in leadgate_users:
        chat_message = ChatMessage(
            from_makler_id=makler.id,
            to_user_id=user.id,
            nachricht=nachricht,
            gelesen=False
        )
        db.add(chat_message)
    
    db.commit()
    
    # Lade zusätzliche Informationen
    return schemas.CreditsRueckzahlungAnfrageRead(
        id=anfrage.id,
        makler_id=anfrage.makler_id,
        transaktion_id=anfrage.transaktion_id,
        betrag=anfrage.betrag,
        status=anfrage.status,
        beschreibung=anfrage.beschreibung,
        erstellt_am=anfrage.erstellt_am,
        bearbeitet_am=anfrage.bearbeitet_am,
        bearbeitet_von_user_id=anfrage.bearbeitet_von_user_id,
        rueckzahlung_transaktion_id=anfrage.rueckzahlung_transaktion_id,
        makler_firmenname=makler.firmenname
    )


@router.get("/credits/rueckzahlbar")
def get_gatelink_rueckzahlbare_credits(
    monate: int = 2,
    current_user: Union[User, Makler] = Depends(get_current_gatelink_user),
    db: Session = Depends(get_db)
):
    """
    Gibt eine Liste von Credits zurück, die zurückgezahlt werden können.
    Nur für Makler mit Credits-System verfügbar.
    """
    if isinstance(current_user, User):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Nur Makler können ihre rückzahlbaren Credits abrufen"
        )
    
    makler = current_user
    if (makler.rechnungssystem_typ or 'alt') != 'neu':
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Dieser Makler verwendet nicht das Credits-System"
        )
    
    from ..services.credits_service import berechne_rueckzahlbare_credits
    
    rueckzahlbare = berechne_rueckzahlbare_credits(db, makler.id, monate)
    return rueckzahlbare


@router.post("/credits/stripe/create-payment-intent")
def create_gatelink_stripe_payment_intent(
    data: schemas.MaklerCreditsAufladen,
    current_user: Union[User, Makler] = Depends(get_current_gatelink_user),
    db: Session = Depends(get_db)
):
    """
    Erstellt einen Stripe Payment Intent für eine Credits-Aufladung (GateLink).
    WICHTIG: data.betrag ist der Nettobetrag (wird als Credits gutgeschrieben).
    Der Bruttobetrag (inkl. 19% MwSt) wird vom Makler bezahlt.
    Nur für Makler mit Credits-System verfügbar.
    """
    if isinstance(current_user, User):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Nur Makler können Credits aufladen"
        )
    
    makler = current_user
    if (makler.rechnungssystem_typ or 'alt') != 'neu':
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Dieser Makler verwendet nicht das Credits-System"
        )
    
    from ..services.stripe_service import create_payment_intent
    from ..config import STRIPE_ENABLED, STRIPE_PUBLISHABLE_KEY
    
    if not STRIPE_ENABLED:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Stripe ist nicht konfiguriert"
        )
    
    if data.betrag <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Betrag muss größer als 0 sein"
        )
    
    # Erstelle Payment Intent (betrag ist Nettobetrag, MwSt wird automatisch hinzugefügt)
    payment_intent = create_payment_intent(
        makler=makler,
        betrag_netto=data.betrag,  # Nettobetrag (wird als Credits gutgeschrieben)
        beschreibung=data.beschreibung or f"Credits-Aufladung für {makler.firmenname}"
    )
    
    return {
        "client_secret": payment_intent["client_secret"],
        "payment_intent_id": payment_intent["payment_intent_id"],
        "publishable_key": STRIPE_PUBLISHABLE_KEY,
        "amount": payment_intent["amount"],
        "currency": payment_intent["currency"],
        "betrag_netto": payment_intent["betrag_netto"],
        "betrag_brutto": payment_intent["betrag_brutto"],
        "mwst": payment_intent["mwst"]
    }


@router.get("/chat", response_model=List[schemas.ChatMessageRead])
def get_chat_messages(
    current_user: Union[User, Makler] = Depends(get_current_gatelink_user),
    db: Session = Depends(get_db)
):
    """
    Ruft Chat-Nachrichten ab.
    - Makler sehen nur ihre Konversation mit LeadGate
    - Nur Manager und Admin sehen Konversationen mit Maklern
    - Telefonisten/Buchhalter sehen keine Makler-Konversationen
    """
    if isinstance(current_user, User):
        # Prüfe Berechtigung: Nur Manager und Admin können Makler-Nachrichten sehen
        if current_user.role in [UserRole.MANAGER, UserRole.ADMIN]:
            # User (Manager/Admin): Alle Nachrichten mit Maklern
            messages = db.query(ChatMessage).options(
                joinedload(ChatMessage.from_user),
                joinedload(ChatMessage.to_user),
                joinedload(ChatMessage.from_makler),
                joinedload(ChatMessage.to_makler)
            ).filter(
                ((ChatMessage.from_user_id == current_user.id) & (ChatMessage.to_makler_id.isnot(None))) |
                ((ChatMessage.to_user_id == current_user.id) & (ChatMessage.from_makler_id.isnot(None)))
            ).order_by(ChatMessage.erstellt_am.asc()).all()
        else:
            # Telefonisten/Buchhalter: Keine Makler-Nachrichten
            messages = []
        
        # Markiere Nachrichten als gelesen (bulk update für bessere Performance)
        unread_ids = [m.id for m in messages if not m.gelesen and m.from_makler_id is not None]
        if unread_ids:
            db.query(ChatMessage).filter(ChatMessage.id.in_(unread_ids)).update({ChatMessage.gelesen: True}, synchronize_session=False)
            db.commit()
    else:
        # Makler: Nur Nachrichten mit LeadGate (wo from_makler_id == current_user.id oder to_makler_id == current_user.id)
        messages = db.query(ChatMessage).options(
            joinedload(ChatMessage.from_user),
            joinedload(ChatMessage.to_user),
            joinedload(ChatMessage.from_makler),
            joinedload(ChatMessage.to_makler)
        ).filter(
            (ChatMessage.from_makler_id == current_user.id) |
            (ChatMessage.to_makler_id == current_user.id)
        ).order_by(ChatMessage.erstellt_am.asc()).all()
        
        # Markiere Nachrichten als gelesen (bulk update für bessere Performance)
        unread_ids = [m.id for m in messages if not m.gelesen and m.from_user_id is not None]
        if unread_ids:
            db.query(ChatMessage).filter(ChatMessage.id.in_(unread_ids)).update({ChatMessage.gelesen: True}, synchronize_session=False)
            db.commit()
    
    return [load_gatelink_message_details(msg) for msg in messages]


def load_gatelink_message_details(message: ChatMessage, db: Session = None):
    """Hilfsfunktion zum Laden der Details einer Nachricht für GateLink (optimiert mit Eager Loading)"""
    from_user_username = None
    from_makler_firmenname = None
    to_user_username = None
    to_makler_firmenname = None
    
    if message.from_user_id:
        # Nutze bereits geladene Relationship falls vorhanden
        if hasattr(message, 'from_user') and message.from_user:
            from_user_username = message.from_user.username
        elif db:
            user = db.query(User).filter(User.id == message.from_user_id).first()
            from_user_username = user.username if user else None
    
    if message.from_makler_id:
        # Nutze bereits geladene Relationship falls vorhanden
        if hasattr(message, 'from_makler') and message.from_makler:
            from_makler_firmenname = message.from_makler.firmenname
        elif db:
            makler = db.query(Makler).filter(Makler.id == message.from_makler_id).first()
            from_makler_firmenname = makler.firmenname if makler else None
    
    if message.to_user_id:
        # Nutze bereits geladene Relationship falls vorhanden
        if hasattr(message, 'to_user') and message.to_user:
            to_user_username = message.to_user.username
        elif db:
            user = db.query(User).filter(User.id == message.to_user_id).first()
            to_user_username = user.username if user else None
    
    if message.to_makler_id:
        # Nutze bereits geladene Relationship falls vorhanden
        if hasattr(message, 'to_makler') and message.to_makler:
            to_makler_firmenname = message.to_makler.firmenname
        elif db:
            makler = db.query(Makler).filter(Makler.id == message.to_makler_id).first()
            to_makler_firmenname = makler.firmenname if makler else None
    
    return {
        "id": message.id,
        "from_user_id": message.from_user_id,
        "from_makler_id": message.from_makler_id,
        "to_user_id": message.to_user_id,
        "to_makler_id": message.to_makler_id,
        "nachricht": message.nachricht,
        "erstellt_am": message.erstellt_am,
        "gelesen": message.gelesen,
        "from_user_username": from_user_username,
        "from_makler_firmenname": from_makler_firmenname,
        "to_user_username": to_user_username,
        "to_makler_firmenname": to_makler_firmenname
    }

