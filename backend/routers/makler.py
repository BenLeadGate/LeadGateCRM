from typing import List
from pathlib import Path
import os
import shutil
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status, UploadFile, File, Form
from typing import Optional
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from .. import schemas
from ..database import get_db
from ..models import Makler, User, MaklerDokument
from ..models.user import UserRole
from ..services.auth_service import get_current_active_user, require_admin_or_manager
from ..logging_config import get_logger

logger = get_logger("makler")

router = APIRouter()

# Verzeichnis für Makler-Dokumente
MAKLER_DOKUMENTE_DIR = Path(__file__).parent.parent.parent / "makler_dokumente"
MAKLER_DOKUMENTE_DIR.mkdir(exist_ok=True)


@router.get("/", response_model=List[schemas.MaklerRead])
def list_makler(
    skip: int = Query(0, ge=0, description="Anzahl zu überspringender Einträge"),
    limit: int = Query(100, ge=1, le=1000, description="Maximale Anzahl zurückzugebender Einträge"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Liefert alle Makler zurück (mit Pagination).
    """
    return db.query(Makler).offset(skip).limit(limit).all()


# WICHTIG: Spezifischere Routen müssen VOR generischen Routen stehen!
# /{makler_id}/controlling muss vor /{makler_id} kommen

@router.get("/{makler_id}/controlling", response_model=dict)
def get_makler_controlling(
    makler_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin_or_manager)
):
    """
    Liefert alle Controlling-Daten für einen Makler (nur für Admin oder Manager).
    Inkludiert: Makler-Daten, Statistiken, Rechnungen, Dokumente, Leads.
    """
    from typing import Dict, Any
    from datetime import datetime
    from sqlalchemy import extract, func, or_
    from ..models.lead import Lead
    from ..models.rechnung import Rechnung
    from ..services.abrechnung_service import berechne_vertragsmonat, bestimme_preis_pro_lead, ist_makler_in_monat_aktiv
    
    makler = db.query(Makler).filter(Makler.id == makler_id).first()
    if not makler:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Makler nicht gefunden"
        )
    
    jetzt = datetime.now()
    aktueller_monat = jetzt.month
    aktuelles_jahr = jetzt.year
    
    # Lead-Statistiken
    anzahl_leads_gesamt = db.query(Lead).filter(Lead.makler_id == makler.id).count()
    anzahl_leads_geliefert = db.query(Lead).filter(
        Lead.makler_id == makler.id,
        Lead.status == "qualifiziert"
    ).count()
    anzahl_leads_neu = db.query(Lead).filter(
        Lead.makler_id == makler.id,
        Lead.status.in_(["neu", "unqualifiziert"])
    ).count()
    anzahl_leads_storniert = db.query(Lead).filter(
        Lead.makler_id == makler.id,
        Lead.status == "storniert"
    ).count()
    
    # Monatsstatistik (aktueller Monat)
    vertragsmonat = berechne_vertragsmonat(makler.vertragsstart_datum, aktueller_monat, aktuelles_jahr)
    preis_pro_lead = bestimme_preis_pro_lead(makler, vertragsmonat)
    ist_aktiv = ist_makler_in_monat_aktiv(makler, aktueller_monat, aktuelles_jahr, db)
    
    if makler.monatliche_soll_leads is not None:
        soll_leads = makler.monatliche_soll_leads
    elif vertragsmonat == 1 and makler.testphase_leads > 0:
        soll_leads = makler.testphase_leads
    else:
        soll_leads = None
    
    ist_leads = (
        db.query(Lead)
        .filter(
            Lead.makler_id == makler.id,
            Lead.status == "qualifiziert",
            Lead.qualifiziert_am.isnot(None),
            extract("month", Lead.qualifiziert_am) == aktueller_monat,
            extract("year", Lead.qualifiziert_am) == aktuelles_jahr,
        )
        .count()
    ) if ist_aktiv else 0
    
    # Berechne Lieferung in Prozent
    lieferung_prozent = None
    if soll_leads and soll_leads > 0:
        if makler.vertrag_pausiert == 1:
            # Wenn pausiert, setze auf 100%
            lieferung_prozent = 100.0
        else:
            lieferung_prozent = (ist_leads / soll_leads * 100) if soll_leads > 0 else 0.0
    
    # Rechnungen-Statistiken
    rechnungen = db.query(Rechnung).filter(Rechnung.makler_id == makler.id).order_by(
        Rechnung.jahr.desc(), Rechnung.monat.desc()
    ).limit(12).all()
    
    gesamtumsatz_result = db.query(func.sum(Rechnung.gesamtbetrag)).filter(
        Rechnung.makler_id == makler.id
    ).scalar()
    gesamtumsatz = float(gesamtumsatz_result) if gesamtumsatz_result else 0.0
    
    durchschnitt_umsatz = gesamtumsatz / len(rechnungen) if len(rechnungen) > 0 else 0.0
    
    # Letzte Leads (neuere zuerst)
    letzte_leads = db.query(Lead).filter(
        Lead.makler_id == makler.id
    ).order_by(Lead.erstellt_am.desc()).limit(20).all()
    
    # Lade Lead-Details
    from .leads import load_lead_details
    leads_details = [load_lead_details(lead, db) for lead in letzte_leads]
    
    # Dokumente
    dokumente = db.query(MaklerDokument).filter(
        MaklerDokument.makler_id == makler.id
    ).order_by(MaklerDokument.hochgeladen_am.desc()).all()
    
    # Status-Information
    status_info = {
        "aktiv": ist_aktiv,
        "pausiert": makler.vertrag_pausiert == 1,
        "gekuendigt": (
            makler.vertrag_bis is not None and
            makler.vertrag_bis < datetime(aktuelles_jahr, aktueller_monat, 28).date()
        )
    }
    
    return {
        "makler": {
            "id": makler.id,
            "firmenname": makler.firmenname,
            "ansprechpartner": makler.ansprechpartner,
            "email": makler.email,
            "adresse": makler.adresse,
            "vertragsstart_datum": makler.vertragsstart_datum.isoformat() if makler.vertragsstart_datum else None,
            "testphase_leads": makler.testphase_leads,
            "testphase_preis": makler.testphase_preis,
            "standard_preis": makler.standard_preis,
            "monatliche_soll_leads": makler.monatliche_soll_leads,
            "rechnungs_code": makler.rechnungs_code,
            "gebiet": makler.gebiet,
            "notizen": makler.notizen,
            "vertrag_pausiert": makler.vertrag_pausiert,
            "vertrag_bis": makler.vertrag_bis.isoformat() if makler.vertrag_bis else None,
        },
        "statistiken": {
            "leads": {
                "gesamt": anzahl_leads_gesamt,
                "geliefert": anzahl_leads_geliefert,
                "neu": anzahl_leads_neu,
                "storniert": anzahl_leads_storniert,
            },
            "monat_aktuell": {
                "monat": aktueller_monat,
                "jahr": aktuelles_jahr,
                "vertragsmonat": vertragsmonat,
                "soll_leads": soll_leads,
                "ist_leads": ist_leads,
                "preis_pro_lead": preis_pro_lead,
                "ist_aktiv": ist_aktiv,
                "lieferung_prozent": lieferung_prozent,
            },
            "umsatz": {
                "gesamt": gesamtumsatz,
                "durchschnitt": durchschnitt_umsatz,
                "anzahl_rechnungen": len(rechnungen),
            }
        },
        "rechnungen": [
            {
                "id": r.id,
                "rechnungstyp": r.rechnungstyp,
                "monat": r.monat,
                "jahr": r.jahr,
                "anzahl_leads": r.anzahl_leads,
                "preis_pro_lead": r.preis_pro_lead,
                "gesamtbetrag": r.gesamtbetrag,
                "status": r.status,
                "erstellt_am": r.erstellt_am.isoformat() if r.erstellt_am else None,
            }
            for r in rechnungen
        ],
        "leads": leads_details,
        "dokumente": [
            {
                "id": d.id,
                "dateiname": d.dateiname,
                "beschreibung": d.beschreibung,
                "hochgeladen_am": d.hochgeladen_am.isoformat() if d.hochgeladen_am else None,
            }
            for d in dokumente
        ],
        "status": status_info,
    }


@router.get("/{makler_id}", response_model=schemas.MaklerRead)
def get_makler(
    makler_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    makler = db.query(Makler).filter(Makler.id == makler_id).first()
    if not makler:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Makler nicht gefunden"
        )
    return makler


@router.post(
    "/", response_model=schemas.MaklerRead, status_code=status.HTTP_201_CREATED
)
def create_makler(
    data: schemas.MaklerCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin_or_manager)
):
    """
    Erstellt einen neuen Makler (nur für Admin oder Manager).
    Buchhalter und Telefonist können keine Makler erstellen.
    """
    # Verwende model_dump() statt dict() für Pydantic V2 Kompatibilität
    makler_data = data.model_dump() if hasattr(data, 'model_dump') else data.dict()
    
    logger.debug(f"Erstelle Makler mit Daten: {makler_data}")
    
    # Erstelle Makler-Objekt - verwende **makler_data für alle Felder
    # Das ist einfacher und sicherer
    makler = Makler(**makler_data)
    makler.created_by_user_id = current_user.id
    makler.modified_by_user_id = current_user.id
    
    db.add(makler)
    try:
        db.commit()
    except Exception as e:
        db.rollback()
        # Prüfe ob es ein Unique-Constraint-Fehler ist
        error_str = str(e).lower()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Fehler beim Erstellen des Maklers: {str(e)}"
        )
    db.refresh(makler)
    logger.info(f"Makler erstellt: ID={makler.id}, Firmenname={makler.firmenname}")
    
    return makler


@router.put("/{makler_id}", response_model=schemas.MaklerRead)
def update_makler(
    makler_id: int,
    data: schemas.MaklerUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin_or_manager)
):
    """
    Aktualisiert einen Makler (nur für Admin oder Manager).
    Buchhalter und Telefonist können keine Makler bearbeiten.
    """
    makler = db.query(Makler).filter(Makler.id == makler_id).first()
    if not makler:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Makler nicht gefunden"
        )

    update_data = data.dict(exclude_unset=True)
    for key, value in update_data.items():
        # GateLink-Passwort: Nur aktualisieren wenn ein Wert gesetzt ist (nicht None)
        if key == 'gatelink_password' and value is None:
            continue
        setattr(makler, key, value)
    
    makler.modified_by_user_id = current_user.id

    db.commit()
    db.refresh(makler)
    return makler


@router.delete(
    "/{makler_id}", status_code=status.HTTP_204_NO_CONTENT
)
def delete_makler(
    makler_id: int, 
    db: Session = Depends(get_db),
    cascade: bool = Query(False, description="Wenn True, werden auch alle zugehörigen Leads und Rechnungen gelöscht"),
    current_user: User = Depends(require_admin_or_manager)
):
    """
    Löscht einen Makler.
    
    Args:
        makler_id: ID des zu löschenden Maklers
        cascade: Wenn True, werden auch alle zugehörigen Leads und Rechnungen gelöscht
    """
    from ..models import Lead, Rechnung
    
    makler = db.query(Makler).filter(Makler.id == makler_id).first()
    if not makler:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Makler nicht gefunden"
        )
    
    # Prüfe ob noch Leads oder Rechnungen existieren
    anzahl_leads = db.query(Lead).filter(Lead.makler_id == makler_id).count()
    anzahl_rechnungen = db.query(Rechnung).filter(Rechnung.makler_id == makler_id).count()
    
    if anzahl_leads > 0 or anzahl_rechnungen > 0:
        if cascade:
            # Lösche zuerst alle abhängigen Daten
            db.query(Lead).filter(Lead.makler_id == makler_id).delete()
            db.query(Rechnung).filter(Rechnung.makler_id == makler_id).delete()
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Makler kann nicht gelöscht werden: {anzahl_leads} Lead(s) und {anzahl_rechnungen} Rechnung(en) vorhanden. Bitte zuerst löschen oder mit cascade=true löschen."
            )
    
    db.delete(makler)
    db.commit()
    return None


# ========== Makler-Dokumente Endpoints ==========

@router.post("/{makler_id}/dokumente", status_code=status.HTTP_201_CREATED)
async def upload_makler_dokument(
    makler_id: int,
    file: UploadFile = File(...),
    beschreibung: str = Form(None),
    current_user: User = Depends(require_admin_or_manager),
    db: Session = Depends(get_db)
):
    """
    Lädt ein Dokument (PDF) für einen Makler hoch.
    Nur für Admin oder Manager.
    """
    # Prüfe ob Makler existiert
    makler = db.query(Makler).filter(Makler.id == makler_id).first()
    if not makler:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Makler nicht gefunden"
        )
    
    # Prüfe ob es eine PDF-Datei ist
    if not file.filename or not file.filename.lower().endswith('.pdf'):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Nur PDF-Dateien werden unterstützt"
        )
    
    try:
        # Sichere Dateinamen
        safe_filename = os.path.basename(file.filename)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        gespeicherter_dateiname = f"{makler_id}_{timestamp}_{safe_filename}"
        file_path = MAKLER_DOKUMENTE_DIR / gespeicherter_dateiname
        
        logger.debug(f"Speichere Datei: {file_path}")
        
        # Stelle sicher, dass das Verzeichnis existiert
        MAKLER_DOKUMENTE_DIR.mkdir(parents=True, exist_ok=True)
        
        # Speichere die Datei
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        file_size = file_path.stat().st_size
        logger.debug(f"Datei gespeichert, Größe: {file_size} bytes")
        
        # Erstelle Datenbank-Eintrag
        try:
            dokument = MaklerDokument(
                makler_id=makler_id,
                dateiname=safe_filename,
                gespeicherter_dateiname=gespeicherter_dateiname,
                hochgeladen_von_user_id=current_user.id,
                beschreibung=beschreibung
            )
            db.add(dokument)
            db.flush()  # Flush um die ID zu bekommen, aber noch nicht committen
            db.commit()
            db.refresh(dokument)
            logger.info(f"Dokument hochgeladen: ID={dokument.id}, Makler={makler_id}, Dateiname={safe_filename}")
        except Exception as db_error:
            db.rollback()
            logger.error(f"Datenbank-Fehler beim Speichern: {db_error}", exc_info=True)
            raise
        
        return {
            "id": dokument.id,
            "makler_id": dokument.makler_id,
            "dateiname": dokument.dateiname,
            "hochgeladen_am": dokument.hochgeladen_am.isoformat(),
            "beschreibung": dokument.beschreibung,
            "message": "Dokument erfolgreich hochgeladen"
        }
    except Exception as e:
        error_message = str(e)
        logger.error(f"Fehler beim Hochladen des Dokuments: {error_message}", exc_info=True)
        # Lösche Datei falls Fehler beim Speichern in DB
        if 'file_path' in locals() and file_path and file_path.exists():
            try:
                file_path.unlink()
                logger.debug(f"Datei gelöscht nach Fehler: {file_path}")
            except Exception as del_error:
                logger.error(f"Konnte Datei nicht löschen: {del_error}")
        
        # Prüfe ob es ein Datenbankfehler ist
        if "no such table" in error_message.lower() or "makler_dokumente" in error_message.lower():
            error_detail = "Datenbank-Tabelle nicht gefunden. Bitte starten Sie den Server neu."
        else:
            error_detail = f"Fehler beim Hochladen des Dokuments: {error_message}"
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=error_detail
        )


@router.get("/{makler_id}/dokumente", response_model=List[dict])
def list_makler_dokumente(
    makler_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Listet alle Dokumente eines Maklers auf.
    """
    try:
        # Prüfe ob Makler existiert
        makler = db.query(Makler).filter(Makler.id == makler_id).first()
        if not makler:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Makler nicht gefunden"
            )
        
        dokumente = db.query(MaklerDokument).filter(
            MaklerDokument.makler_id == makler_id
        ).order_by(MaklerDokument.hochgeladen_am.desc()).all()
        
        result = []
        for dok in dokumente:
            result.append({
                "id": dok.id,
                "makler_id": dok.makler_id,
                "dateiname": dok.dateiname,
                "hochgeladen_am": dok.hochgeladen_am.isoformat() if dok.hochgeladen_am else None,
                "beschreibung": dok.beschreibung,
                "hochgeladen_von_user_id": dok.hochgeladen_von_user_id
            })
        
        return result
    except HTTPException:
        raise
    except Exception as e:
        import logging
        logging.error(f"Fehler beim Laden der Dokumente für Makler {makler_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Fehler beim Laden der Dokumente: {str(e)}"
        )


@router.get("/{makler_id}/dokumente/{dokument_id}/download")
async def download_makler_dokument(
    makler_id: int,
    dokument_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Lädt ein Dokument eines Maklers herunter.
    """
    dokument = db.query(MaklerDokument).filter(
        MaklerDokument.id == dokument_id,
        MaklerDokument.makler_id == makler_id
    ).first()
    
    if not dokument:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Dokument nicht gefunden"
        )
    
    file_path = MAKLER_DOKUMENTE_DIR / dokument.gespeicherter_dateiname
    
    if not file_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Datei nicht gefunden"
        )
    
    return FileResponse(
        path=str(file_path),
        filename=dokument.dateiname,
        media_type="application/pdf"
    )


@router.delete("/{makler_id}/dokumente/{dokument_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_makler_dokument(
    makler_id: int,
    dokument_id: int,
    current_user: User = Depends(require_admin_or_manager),
    db: Session = Depends(get_db)
):
    """
    Löscht ein Dokument eines Maklers.
    Nur für Admin oder Manager.
    """
    dokument = db.query(MaklerDokument).filter(
        MaklerDokument.id == dokument_id,
        MaklerDokument.makler_id == makler_id
    ).first()
    
    if not dokument:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Dokument nicht gefunden"
        )
    
    # Lösche Datei
    file_path = MAKLER_DOKUMENTE_DIR / dokument.gespeicherter_dateiname
    if file_path.exists():
        file_path.unlink()
    
    # Lösche Datenbank-Eintrag
    db.delete(dokument)
    db.commit()
    
    return None


