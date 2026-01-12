from typing import List
from datetime import datetime
from sqlalchemy import func
import random

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from .. import schemas
from ..database import get_db
from ..models import Lead, Makler, User
from ..models.user import UserRole
from ..services.auth_service import get_current_active_user, require_admin_or_manager, require_manager_or_telefonist

router = APIRouter()


def generate_unique_lead_nummer(db: Session) -> int:
    """
    Generiert eine eindeutige, zufällige Lead-Nummer.
    Die Nummer liegt zwischen 10000 und 99999 (5-stellig).
    Prüft, ob die Nummer bereits existiert und generiert bei Bedarf eine neue.
    """
    max_attempts = 1000  # Maximal 1000 Versuche, um eine eindeutige Nummer zu finden
    existing_numbers = set(db.query(Lead.lead_nummer).filter(Lead.lead_nummer.isnot(None)).all())
    existing_numbers = {num[0] for num in existing_numbers}  # Konvertiere zu Set von Integers
    
    for _ in range(max_attempts):
        # Generiere zufällige 5-stellige Nummer zwischen 10000 und 99999
        nummer = random.randint(10000, 99999)
        if nummer not in existing_numbers:
            return nummer
    
    # Falls nach 1000 Versuchen keine eindeutige Nummer gefunden wurde (extrem unwahrscheinlich),
    # verwende einen größeren Bereich
    for _ in range(max_attempts):
        nummer = random.randint(100000, 999999)  # 6-stellig
        if nummer not in existing_numbers:
            return nummer
    
    # Letzter Fallback: Verwende Timestamp-basierte Nummer
    import time
    nummer = int(time.time() * 100) % 1000000  # Timestamp-basiert, aber 6-stellig
    while nummer in existing_numbers:
        nummer = (nummer + 1) % 1000000
    return nummer


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


def load_lead_details(lead: Lead, db: Session):
    """Hilfsfunktion zum Laden der Details eines Leads mit qualifiziert_von_username"""
    qualifiziert_von_username = None
    if lead.qualifiziert_von_user_id:
        user = db.query(User).filter(User.id == lead.qualifiziert_von_user_id).first()
        qualifiziert_von_username = user.username if user else None
    
    # Lade auch bearbeitet_von_username für Locking-Info
    bearbeitet_von_username = None
    if lead.bearbeitet_von_user_id:
        user = db.query(User).filter(User.id == lead.bearbeitet_von_user_id).first()
        bearbeitet_von_username = user.username if user else None
    
    # Berechne moegliche_makler_ids dynamisch basierend auf aktuellen Makler-Gebieten
    moegliche_makler_ids_list = []
    if lead.postleitzahl:
        moegliche_makler_ids_list = find_makler_by_postleitzahl(db, lead.postleitzahl)
    
    # Konvertiere zu kommagetrenntem String (wie in der Datenbank gespeichert)
    moegliche_makler_ids_str = ', '.join(map(str, moegliche_makler_ids_list)) if moegliche_makler_ids_list else None
    
    # Konvertiere Lead zu Dict und füge qualifiziert_von_username hinzu
    lead_dict = {
        "id": lead.id,
        "lead_nummer": lead.lead_nummer,
        "makler_id": lead.makler_id,
        "erstellt_am": lead.erstellt_am,
        "status": lead.status.value if hasattr(lead.status, 'value') else lead.status,
        "created_by_user_id": lead.created_by_user_id,
        "anbieter_name": lead.anbieter_name,
        "postleitzahl": lead.postleitzahl,
        "ort": lead.ort,
        "grundstuecksflaeche": lead.grundstuecksflaeche,
        "wohnflaeche": lead.wohnflaeche,
        "preis": lead.preis,
        "telefonnummer": lead.telefonnummer,
        "features": lead.features,
        "immobilien_typ": lead.immobilien_typ,
        "baujahr": lead.baujahr,
        "lage": lead.lage,
        "beschreibung": lead.beschreibung,
        "moegliche_makler_ids": moegliche_makler_ids_str,  # Dynamisch berechnet
        "kontakt_datum": lead.kontakt_datum,
        "kontakt_zeitraum": lead.kontakt_zeitraum,
        "qualifiziert_am": lead.qualifiziert_am,
        "qualifiziert_von_user_id": lead.qualifiziert_von_user_id,
        "qualifiziert_von_username": qualifiziert_von_username,
        "bearbeitet_von_user_id": lead.bearbeitet_von_user_id,
        "bearbeitet_seit": lead.bearbeitet_seit.isoformat() if lead.bearbeitet_seit else None,
        "bearbeitet_von_username": bearbeitet_von_username,
        "makler_status": lead.makler_status,
        "makler_beschreibung": lead.makler_beschreibung,
        "makler_status_geaendert_am": lead.makler_status_geaendert_am,
        "telefon_kontakt_ergebnis": lead.telefon_kontakt_ergebnis,
        "telefon_kontakt_datum": lead.telefon_kontakt_datum,
        "telefon_kontakt_uhrzeit": lead.telefon_kontakt_uhrzeit,
        "termin_vereinbart": lead.termin_vereinbart,
        "termin_ort": lead.termin_ort,
        "termin_datum": lead.termin_datum,
        "termin_uhrzeit": lead.termin_uhrzeit,
        "termin_notiz": lead.termin_notiz,
        "absage": lead.absage,
        "absage_notiz": lead.absage_notiz,
        "zweit_termin_vereinbart": lead.zweit_termin_vereinbart,
        "zweit_termin_ort": lead.zweit_termin_ort,
        "zweit_termin_datum": lead.zweit_termin_datum,
        "zweit_termin_uhrzeit": lead.zweit_termin_uhrzeit,
        "zweit_termin_notiz": lead.zweit_termin_notiz,
        "maklervertrag_unterschrieben": lead.maklervertrag_unterschrieben,
        "maklervertrag_notiz": lead.maklervertrag_notiz,
        "immobilie_verkauft": lead.immobilie_verkauft,
        "immobilie_verkauft_datum": lead.immobilie_verkauft_datum,
        "immobilie_verkauft_preis": lead.immobilie_verkauft_preis,
        "beteiligungs_prozent": lead.beteiligungs_prozent,
        "favorit": lead.favorit,
        "makler_angesehen": lead.makler_angesehen
    }
    
    # Füge Makler-Firmenname hinzu, falls vorhanden
    if lead.makler_id:
        makler = db.query(Makler).filter(Makler.id == lead.makler_id).first()
        if makler:
            lead_dict["makler_firmenname"] = makler.firmenname
    
    return lead_dict


class BulkLeadCreate(BaseModel):
    makler_id: int
    anzahl: int
    status: schemas.LeadStatus = schemas.LeadStatus.GELIEFERT


@router.get("/", response_model=List[schemas.LeadRead])
def list_leads(
    skip: int = Query(0, ge=0, description="Anzahl zu überspringender Einträge"),
    limit: int = Query(100, ge=1, le=1000, description="Maximale Anzahl zurückzugebender Einträge"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Liefert alle Leads zurück (mit Pagination).
    """
    leads = db.query(Lead).order_by(Lead.erstellt_am.desc()).offset(skip).limit(limit).all()
    lead_dicts = [load_lead_details(lead, db) for lead in leads]
    # Konvertiere Dictionaries explizit zu Pydantic-Modellen
    return [schemas.LeadRead(**lead_dict) for lead_dict in lead_dicts]


@router.get("/{lead_id}", response_model=schemas.LeadRead)
def get_lead(
    lead_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    lead = db.query(Lead).filter(Lead.id == lead_id).first()
    if not lead:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Lead nicht gefunden"
        )
    lead_dict = load_lead_details(lead, db)
    # Konvertiere Dictionary explizit zu Pydantic-Modell
    return schemas.LeadRead(**lead_dict)


@router.post("/", response_model=schemas.LeadRead, status_code=status.HTTP_201_CREATED)
def create_lead(
    data: schemas.LeadCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_manager_or_telefonist)
):
    """
    Erstellt einen neuen Lead (nur für Manager oder Telefonist).
    Buchhalter können keine Leads erstellen.
    """
    # Validierung: Makler muss existieren (falls angegeben)
    makler = None
    if data.makler_id:
        makler = db.query(Makler).filter(Makler.id == data.makler_id).first()
        if not makler:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Makler für diesen Lead existiert nicht",
            )

    # Generiere eindeutige zufällige Lead-Nummer
    lead_nummer = generate_unique_lead_nummer(db)
    
    lead = Lead(
        lead_nummer=lead_nummer,
        makler_id=data.makler_id,
        status=data.status.value,
        erstellt_am=data.erstellt_am,
        created_by_user_id=current_user.id,
        anbieter_name=data.anbieter_name,
        postleitzahl=data.postleitzahl,
        ort=data.ort,
        grundstuecksflaeche=data.grundstuecksflaeche,
        wohnflaeche=data.wohnflaeche,
        preis=data.preis,
        telefonnummer=data.telefonnummer,
        features=data.features,
        immobilien_typ=data.immobilien_typ,
        baujahr=data.baujahr,
        lage=data.lage,
        beschreibung=data.beschreibung
    )
    db.add(lead)
    db.commit()
    db.refresh(lead)
    lead_dict = load_lead_details(lead, db)
    return schemas.LeadRead(**lead_dict)


@router.put("/{lead_id}", response_model=schemas.LeadRead)
def update_lead(
    lead_id: int,
    data: schemas.LeadUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Aktualisiert einen Lead. 
    - Status kann von allen aktiven Benutzern geändert werden
    - Beschreibung kann von Telefonisten, Managern und Admins hinzugefügt/bearbeitet werden
    """
    lead = db.query(Lead).filter(Lead.id == lead_id).first()
    if not lead:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Lead nicht gefunden"
        )

    update_data = data.dict(exclude_unset=True)
    
    # Locking-System: Prüfe ob Lead von einem anderen Telefonisten bearbeitet wird
    if current_user.role == "telefonist" and lead.status == "unqualifiziert":
        from ..services.lead_empfehlung_service import ist_lead_gesperrt
        if ist_lead_gesperrt(lead, aktueller_user_id=current_user.id):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Dieser Lead wird gerade von einem anderen Telefonisten bearbeitet"
            )
        
        # Setze Lock: Dieser Telefonist bearbeitet jetzt den Lead
        lead.bearbeitet_von_user_id = current_user.id
        lead.bearbeitet_seit = datetime.utcnow()
    
    # Makler-Zuordnung (Telefonisten, Manager, Admin)
    # Wird benötigt wenn Status auf flexrecall oder qualifiziert gesetzt wird
    if "makler_id" in update_data:
        if current_user.role not in [UserRole.TELEFONIST, UserRole.MANAGER, UserRole.ADMIN]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Nur Telefonisten, Manager und Admins können Makler zuordnen"
            )
        makler_id = update_data["makler_id"]
        if makler_id is not None:
            makler = db.query(Makler).filter(Makler.id == makler_id).first()
            if not makler:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Makler existiert nicht"
                )
        
        # Prüfe ob der Lead vorher keinen Makler hatte (wird jetzt zum ersten Mal zugewiesen)
        old_makler_id = lead.makler_id
        lead.makler_id = makler_id
        
        # Wenn ein Lead einem Makler zugewiesen wird (und vorher keiner zugewiesen war)
        # UND ein Status im Update mitgegeben wurde, verwende diesen Status
        # Ansonsten: Wenn Lead unqualifiziert ist, setze automatisch auf qualifiziert
        if makler_id is not None and old_makler_id is None:
            # Prüfe ob Status im Update mitgegeben wurde
            status_in_update = update_data.get("status")
            
            if status_in_update is not None:
                # Status wurde explizit mitgegeben (vom Frontend)
                new_status_value = status_in_update.value if hasattr(status_in_update, 'value') else str(status_in_update)
                
                # Wenn Status "nicht_qualifizierbar" ist, entferne den Lead aus dem System
                if new_status_value == schemas.LeadStatus.NICHT_QUALIFIZIERBAR.value:
                    # Setze Status und entferne qualifiziert_am
                    lead.status = new_status_value
                    lead.qualifiziert_am = None
                    lead.qualifiziert_von_user_id = None
                    lead.makler_id = None  # Entferne Makler-Zuordnung
                    # Lead bleibt in DB, aber wird nicht mehr angezeigt (Status-Filter)
                else:
                    # Für qualifiziert oder flexrecall: Setze qualifiziert_am
                    lead.qualifiziert_am = datetime.utcnow()
                    lead.qualifiziert_von_user_id = current_user.id
                    
                    # Prüfe ob Credits-System aktiv ist (nur für qualifiziert)
                    if new_status_value == schemas.LeadStatus.QUALIFIZIERT.value:
                        makler = db.query(Makler).filter(Makler.id == makler_id).first()
                        if makler and makler.rechnungssystem_typ == "neu":
                            from ..services.credits_service import pruefe_und_buche_credits_fuer_lead
                            qualifiziert_am = datetime.utcnow()
                            
                            # Prüfe ob ohne_credits_qualifizieren gesetzt ist
                            ohne_credits = update_data.get("ohne_credits_qualifizieren", False)
                            
                            if not ohne_credits:
                                # Normale Prüfung: Versuche Credits abzubuchen
                                erfolg, fehlermeldung, preis = pruefe_und_buche_credits_fuer_lead(
                                    db, makler, lead.id, qualifiziert_am
                                )
                                if not erfolg:
                                    # Spezieller Fehlercode für Frontend, um Bestätigung anzufordern
                                    raise HTTPException(
                                        status_code=status.HTTP_402_PAYMENT_REQUIRED,  # 402 = Payment Required
                                        detail=fehlermeldung or "Nicht genug Credits vorhanden"
                                    )
                    
                    # Setze Status
                    lead.status = new_status_value
                    
                    # Locking freigeben
                    lead.bearbeitet_von_user_id = None
                    lead.bearbeitet_seit = None
            else:
                # Kein Status mitgegeben: Automatisch qualifizieren (Fallback für alte Logik)
                current_status_str = lead.status.value if hasattr(lead.status, 'value') else str(lead.status)
                qualifiziert_status = schemas.LeadStatus.QUALIFIZIERT.value
                unqualifiziert_status = schemas.LeadStatus.UNQUALIFIZIERT.value
                
                # Wenn Lead unqualifiziert ist oder noch kein qualifiziert_am hat, qualifiziere ihn
                if current_status_str == unqualifiziert_status or lead.qualifiziert_am is None:
                    # Setze qualifiziert_am und qualifiziert_von_user_id
                    lead.qualifiziert_am = datetime.utcnow()
                    lead.qualifiziert_von_user_id = current_user.id
                    
                    # Prüfe ob Credits-System aktiv ist
                    makler = db.query(Makler).filter(Makler.id == makler_id).first()
                    if makler and makler.rechnungssystem_typ == "neu":
                        from ..services.credits_service import pruefe_und_buche_credits_fuer_lead
                        qualifiziert_am = datetime.utcnow()
                        
                        # Prüfe ob ohne_credits_qualifizieren gesetzt ist
                        ohne_credits = update_data.get("ohne_credits_qualifizieren", False)
                        
                        if not ohne_credits:
                            # Normale Prüfung: Versuche Credits abzubuchen
                            erfolg, fehlermeldung, preis = pruefe_und_buche_credits_fuer_lead(
                                db, makler, lead.id, qualifiziert_am
                            )
                            if not erfolg:
                                # Spezieller Fehlercode für Frontend, um Bestätigung anzufordern
                                raise HTTPException(
                                    status_code=status.HTTP_402_PAYMENT_REQUIRED,  # 402 = Payment Required
                                    detail=fehlermeldung or "Nicht genug Credits vorhanden"
                                )
                    
                    # Setze Status auf qualifiziert
                    lead.status = qualifiziert_status
                    
                    # Locking freigeben: Wenn Lead qualifiziert wird, Lock entfernen
                    lead.bearbeitet_von_user_id = None
                    lead.bearbeitet_seit = None
    
    # Status-Update - prüfe ob makler_id benötigt wird
    if "status" in update_data and update_data["status"] is not None:
        new_status = update_data["status"].value
        # Prüfe ob für flexrecall oder qualifiziert ein Makler benötigt wird
        if new_status in [schemas.LeadStatus.FLEXRECALL.value, schemas.LeadStatus.QUALIFIZIERT.value]:
            if not lead.makler_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Für Status '{new_status}' muss ein Makler zugeordnet sein"
                )
            
            # Prüfe ob Telefonist eine Beschreibung hinzufügen muss
            if current_user.role == "telefonist":
                # Prüfe ob bereits eine Beschreibung vorhanden ist oder in diesem Update gesetzt wird
                aktuelle_beschreibung = lead.beschreibung
                neue_beschreibung = update_data.get("beschreibung")
                
                # Wenn keine Beschreibung vorhanden ist (weder aktuell noch im Update)
                if (not aktuelle_beschreibung or not aktuelle_beschreibung.strip()) and (not neue_beschreibung or not neue_beschreibung.strip()):
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Bitte fügen Sie eine Beschreibung hinzu, bevor Sie den Lead als '{new_status}' markieren"
                    )
    
    # Status-Update (alle aktiven Benutzer)
    # WICHTIG: Prüfe ob Status bereits in der Makler-Zuordnung behandelt wurde
    status_already_handled = False
    if "makler_id" in update_data and "status" in update_data:
        # Status wurde zusammen mit Makler-Zuordnung gesetzt - wurde bereits oben behandelt
        status_already_handled = True
    
    if "status" in update_data and update_data["status"] is not None and not status_already_handled:
        new_status = update_data["status"].value
        # Konvertiere old_status zu String für korrekten Vergleich
        old_status_str = lead.status.value if hasattr(lead.status, 'value') else str(lead.status)
        old_status = lead.status
        
        # Wenn Status auf "nicht_qualifizierbar" gesetzt wird, entferne Makler-Zuordnung
        if new_status == schemas.LeadStatus.NICHT_QUALIFIZIERBAR.value:
            lead.makler_id = None
            lead.qualifiziert_am = None
            lead.qualifiziert_von_user_id = None
        
        # Locking freigeben: Wenn Lead qualifiziert wird oder Status geändert wird, Lock entfernen
        if new_status in [schemas.LeadStatus.QUALIFIZIERT.value, schemas.LeadStatus.FLEXRECALL.value, schemas.LeadStatus.NICHT_QUALIFIZIERBAR.value]:
            lead.bearbeitet_von_user_id = None
            lead.bearbeitet_seit = None
        
        # Wenn Status auf "qualifiziert" geändert wird UND ein Makler zugeordnet ist
        # WICHTIG: Nur wenn der Status tatsächlich geändert wird (nicht bereits qualifiziert)
        if new_status == schemas.LeadStatus.QUALIFIZIERT.value and lead.makler_id and old_status_str != schemas.LeadStatus.QUALIFIZIERT.value:
            # Prüfe Credits für Credits-System
            makler = db.query(Makler).filter(Makler.id == lead.makler_id).first()
            if makler and makler.rechnungssystem_typ == "neu":
                from ..services.credits_service import pruefe_und_buche_credits_fuer_lead, berechne_credits_stand
                qualifiziert_am = datetime.utcnow()
                
                # Prüfe ob ohne_credits_qualifizieren gesetzt ist
                ohne_credits = update_data.get("ohne_credits_qualifizieren", False)
                
                if not ohne_credits:
                    # Normale Prüfung: Versuche Credits abzubuchen
                    erfolg, fehlermeldung, preis = pruefe_und_buche_credits_fuer_lead(
                        db, makler, lead.id, qualifiziert_am
                    )
                    if not erfolg:
                        # Spezieller Fehlercode für Frontend, um Bestätigung anzufordern
                        raise HTTPException(
                            status_code=status.HTTP_402_PAYMENT_REQUIRED,  # 402 = Payment Required
                            detail=fehlermeldung or "Nicht genug Credits vorhanden"
                        )
                else:
                    # Ohne Credits qualifizieren: Prüfe nur ob genug Credits vorhanden wären, aber buche nicht ab
                    from ..services.credits_service import berechne_preis_fuer_lead, zaehle_leads_im_monat
                    qualifiziert_datum = qualifiziert_am.date() if isinstance(qualifiziert_am, datetime) else qualifiziert_am
                    anzahl_leads_im_monat = zaehle_leads_im_monat(
                        db, makler.id, qualifiziert_datum.month, qualifiziert_datum.year
                    ) + 1
                    preis = berechne_preis_fuer_lead(makler, qualifiziert_am, anzahl_leads_im_monat)
                    aktueller_stand = berechne_credits_stand(db, makler.id)
                    # Keine Abbuchung, nur Logging
                    print(f"Lead #{lead.id} wird ohne Credits qualifiziert. Benötigt: {preis:.2f}€, Vorhanden: {aktueller_stand:.2f}€")
            
            # Setze qualifiziert_am auf jetzt und speichere wer qualifiziert hat
            lead.qualifiziert_am = datetime.utcnow()
            lead.qualifiziert_von_user_id = current_user.id
        # Wenn Status auf "flexrecall" geändert wird UND ein Makler zugeordnet ist
        # WICHTIG: Nur wenn der Status tatsächlich geändert wird (nicht bereits flexrecall)
        elif new_status == schemas.LeadStatus.FLEXRECALL.value and lead.makler_id and old_status_str != schemas.LeadStatus.FLEXRECALL.value:
            # Prüfe Credits für Credits-System
            makler = db.query(Makler).filter(Makler.id == lead.makler_id).first()
            if makler and makler.rechnungssystem_typ == "neu":
                from ..services.credits_service import pruefe_und_buche_credits_fuer_lead, berechne_credits_stand
                qualifiziert_am = datetime.utcnow()
                
                # Prüfe ob ohne_credits_qualifizieren gesetzt ist
                ohne_credits = update_data.get("ohne_credits_qualifizieren", False)
                
                if not ohne_credits:
                    # Normale Prüfung: Versuche Credits abzubuchen
                    erfolg, fehlermeldung, preis = pruefe_und_buche_credits_fuer_lead(
                        db, makler, lead.id, qualifiziert_am
                    )
                    if not erfolg:
                        # Spezieller Fehlercode für Frontend, um Bestätigung anzufordern
                        raise HTTPException(
                            status_code=status.HTTP_402_PAYMENT_REQUIRED,  # 402 = Payment Required
                            detail=fehlermeldung or "Nicht genug Credits vorhanden"
                        )
                else:
                    # Ohne Credits qualifizieren: Prüfe nur ob genug Credits vorhanden wären, aber buche nicht ab
                    from ..services.credits_service import berechne_preis_fuer_lead, zaehle_leads_im_monat
                    qualifiziert_datum = qualifiziert_am.date() if isinstance(qualifiziert_am, datetime) else qualifiziert_am
                    anzahl_leads_im_monat = zaehle_leads_im_monat(
                        db, makler.id, qualifiziert_datum.month, qualifiziert_datum.year
                    ) + 1
                    preis = berechne_preis_fuer_lead(makler, qualifiziert_am, anzahl_leads_im_monat)
                    aktueller_stand = berechne_credits_stand(db, makler.id)
                    # Keine Abbuchung, nur Logging
                    print(f"Lead #{lead.id} wird ohne Credits als FlexRecall qualifiziert. Benötigt: {preis:.2f}€, Vorhanden: {aktueller_stand:.2f}€")
            
            # Setze qualifiziert_am auf jetzt und speichere wer qualifiziert hat (für Statistik)
            lead.qualifiziert_am = datetime.utcnow()
            lead.qualifiziert_von_user_id = current_user.id
        # Wenn Status auf "reklamiert" geändert wird, erstelle Erstattung und entferne qualifiziert_von_user_id
        elif new_status == schemas.LeadStatus.REKLAMIERT.value:
            # Erstelle Erstattung für Credits-System
            if lead.makler_id:
                makler = db.query(Makler).filter(Makler.id == lead.makler_id).first()
                if makler and makler.rechnungssystem_typ == "neu":
                    from ..services.credits_service import erstelle_erstattung_fuer_lead
                    erstelle_erstattung_fuer_lead(
                        db, makler, lead.id, f"Erstattung für reklamierten Lead #{lead.id}"
                    )
            
            lead.qualifiziert_von_user_id = None
            lead.qualifiziert_am = None
        
        lead.status = new_status
    
    # Anbieter_Name (Eigentümer) Update (Telefonisten, Manager, Admin)
    if "anbieter_name" in update_data:
        if current_user.role not in [UserRole.TELEFONIST, UserRole.MANAGER, UserRole.ADMIN]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Nur Telefonisten, Manager und Admins können den Eigentümer ändern"
            )
        lead.anbieter_name = update_data["anbieter_name"]
    
    # Preis-Update (Telefonisten, Manager, Admin)
    if "preis" in update_data:
        if current_user.role not in [UserRole.TELEFONIST, UserRole.MANAGER, UserRole.ADMIN]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Nur Telefonisten, Manager und Admins können den Preis ändern"
            )
        lead.preis = update_data["preis"]
    
    # Beschreibung-Update (Telefonisten, Manager, Admin)
    if "beschreibung" in update_data:
        # Prüfe Berechtigung: Telefonisten, Manager und Admins können Beschreibungen bearbeiten
        if current_user.role not in [UserRole.TELEFONIST, UserRole.MANAGER, UserRole.ADMIN]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Nur Telefonisten, Manager und Admins können Beschreibungen hinzufügen"
            )
        lead.beschreibung = update_data["beschreibung"]
    
    # Kontaktzeitpunkt-Update (Telefonisten, Manager, Admin)
    if "kontakt_datum" in update_data:
        if current_user.role not in [UserRole.TELEFONIST, UserRole.MANAGER, UserRole.ADMIN]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Nur Telefonisten, Manager und Admins können Kontaktzeitpunkte setzen"
            )
        lead.kontakt_datum = update_data["kontakt_datum"]
    
    if "kontakt_zeitraum" in update_data:
        if current_user.role not in [UserRole.TELEFONIST, UserRole.MANAGER, UserRole.ADMIN]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Nur Telefonisten, Manager und Admins können Kontaktzeitpunkte setzen"
            )
        lead.kontakt_zeitraum = update_data["kontakt_zeitraum"]

    db.commit()
    db.refresh(lead)
    return load_lead_details(lead, db)


@router.delete("/{lead_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_lead(
    lead_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin_or_manager)
):
    """
    Löscht einen Lead (nur für Admin oder Manager).
    Telefonist kann keine Leads löschen.
    """
    lead = db.query(Lead).filter(Lead.id == lead_id).first()
    if not lead:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Lead nicht gefunden"
        )
    db.delete(lead)
    db.commit()
    return None


@router.post("/bulk", response_model=List[schemas.LeadRead], status_code=status.HTTP_201_CREATED)
def create_bulk_leads(
    data: BulkLeadCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_manager_or_telefonist)
):
    """
    Erstellt mehrere Leads auf einmal für einen Makler (nur für Manager oder Telefonist).
    Buchhalter können keine Leads erstellen.
    """
    makler = db.query(Makler).filter(Makler.id == data.makler_id).first()
    if not makler:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Makler für diese Leads existiert nicht",
        )
    
    leads = []
    for _ in range(data.anzahl):
        lead_nummer = generate_unique_lead_nummer(db)
        lead = Lead(
            lead_nummer=lead_nummer,
            makler_id=data.makler_id,
            status=data.status.value,
            created_by_user_id=current_user.id,
            anbieter_name=None,
            postleitzahl=None,
            ort=None,
            grundstuecksflaeche=None,
            wohnflaeche=None,
            telefonnummer=None,
            features=None,
            beschreibung=None
        )
        db.add(lead)
        db.flush()  # Flush um sicherzustellen, dass die Nummer verwendet wird
        leads.append(lead)
    
    db.commit()
    for lead in leads:
        db.refresh(lead)
    
    lead_dicts = [load_lead_details(lead, db) for lead in leads]
    return [schemas.LeadRead(**lead_dict) for lead_dict in lead_dicts]




