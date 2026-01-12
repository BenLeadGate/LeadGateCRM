from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import Response
from sqlalchemy.orm import Session

from .. import schemas
from ..database import get_db
from ..models import Makler, Rechnung, User
from ..models.user import UserRole
from ..services.abrechnung_service import finde_oder_erzeuge_rechnung
from ..services.pdf_service import generiere_rechnung_pdf
from ..services.auth_service import get_current_active_user, require_buchhalter, require_not_telefonist

router = APIRouter()


@router.get("/", response_model=List[schemas.RechnungRead])
def list_rechnungen(
    skip: int = Query(0, ge=0, description="Anzahl zu überspringender Einträge"),
    limit: int = Query(100, ge=1, le=1000, description="Maximale Anzahl zurückzugebender Einträge"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_not_telefonist)
):
    """
    Liefert alle Rechnungen zurück (mit Pagination, nur für Admin, Manager oder Buchhalter).
    Telefonist hat keinen Zugriff auf Abrechnungen.
    """
    return db.query(Rechnung).order_by(Rechnung.erstellt_am.desc()).offset(skip).limit(limit).all()


@router.get("/verkaufte-leads", response_model=List[schemas.LeadRead])
def get_verkaufte_leads(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_buchhalter)
):
    """
    Liefert alle Leads, die als verkauft markiert sind und noch keine Beteiligungsrechnung haben.
    Nur für Buchhalter oder Admin.
    """
    from ..models.lead import Lead
    
    # Finde Leads mit immobilie_verkauft = 1, die noch keine Beteiligungsrechnung haben
    existing_lead_ids = [
        r.lead_id for r in db.query(Rechnung.lead_id).filter(
            Rechnung.rechnungstyp == "beteiligung",
            Rechnung.lead_id.isnot(None)
        ).all()
    ]
    
    verkaufte_leads = (
        db.query(Lead)
        .filter(
            Lead.immobilie_verkauft == 1,
            Lead.makler_id.isnot(None)
        )
        .order_by(Lead.immobilie_verkauft_datum.desc().nullslast(), Lead.id.desc())
        .all()
    )
    
    # Filtere Leads mit bestehender Beteiligungsrechnung heraus
    verkaufte_leads = [l for l in verkaufte_leads if l.id not in existing_lead_ids]
    
    # Verwende load_lead_details aus leads.py, um konsistente Serialisierung zu gewährleisten
    try:
        from .leads import load_lead_details
        lead_dicts = [load_lead_details(lead, db) for lead in verkaufte_leads]
        return [schemas.LeadRead(**lead_dict) for lead_dict in lead_dicts]
    except Exception as e:
        # Fallback: Wenn Import fehlschlägt, verwende einfache Serialisierung
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Fehler beim Laden der Lead-Details: {str(e)}"
        )


@router.post(
    "/monat/{makler_id}",
    response_model=schemas.RechnungRead,
    status_code=status.HTTP_201_CREATED,
)
def abrechnung_monat_fuer_makler(
    makler_id: int,
    payload: schemas.MonatsabrechnungRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_buchhalter)
):
    """
    Erstellt (falls noch nicht vorhanden) eine Monatsrechnung für einen Makler (nur für Buchhalter oder Admin).
    """
    makler = db.query(Makler).filter(Makler.id == makler_id).first()
    if not makler:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Makler nicht gefunden"
        )

    rechnung, created = finde_oder_erzeuge_rechnung(
        db, makler, payload.monat, payload.jahr
    )
    
    # Tracking: Wer hat die Rechnung erstellt
    if created:
        rechnung.created_by_user_id = current_user.id
        db.commit()
        db.refresh(rechnung)

    # Wenn Rechnung bereits existierte, trotzdem 200 zurückgeben, aber ohne Neu-Erstellung
    if not created:
        # Semantisch eher 200, aber wir belassen 201 laut Signatur;
        # alternativ könnte man hier ein anderes Schema/Status nutzen.
        return rechnung

    return rechnung


@router.post(
    "/beteiligung",
    response_model=schemas.RechnungRead,
    status_code=status.HTTP_201_CREATED,
)
def create_beteiligungsabrechnung(
    payload: schemas.BeteiligungsabrechnungRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_buchhalter)
):
    """
    Erstellt eine Beteiligungsabrechnung für einen verkauften Lead.
    Nur für Buchhalter oder Admin.
    """
    from ..models.lead import Lead
    from sqlalchemy import exists
    
    # Prüfe ob Lead existiert und verkauft ist
    lead = db.query(Lead).filter(Lead.id == payload.lead_id).first()
    if not lead:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Lead nicht gefunden"
        )
    
    if lead.immobilie_verkauft != 1:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Lead ist nicht als verkauft markiert"
        )
    
    if not lead.makler_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Lead ist keinem Makler zugeordnet"
        )
    
    # Prüfe ob bereits eine Beteiligungsrechnung existiert
    existing = db.query(Rechnung).filter(
        Rechnung.rechnungstyp == "beteiligung",
        Rechnung.lead_id == payload.lead_id
    ).first()
    
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Für diesen Lead existiert bereits eine Beteiligungsrechnung"
        )
    
    # Prüfe ob notwendige Felder vorhanden sind
    if not lead.immobilie_verkauft_preis or not lead.beteiligungs_prozent:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Verkaufspreis und Beteiligungsprozentsatz müssen gesetzt sein"
        )
    
    # Parse Verkaufspreis (kann Format wie "250.000 €" haben)
    verkaufspreis_str = lead.immobilie_verkauft_preis.replace('.', '').replace(',', '.').replace('€', '').strip()
    try:
        verkaufspreis = float(verkaufspreis_str)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ungültiges Format für Verkaufspreis"
        )
    
    beteiligungs_prozent = lead.beteiligungs_prozent
    
    # Berechne unseren Anteil am Verkaufspreis
    unser_anteil_am_verkauf = verkaufspreis * (beteiligungs_prozent / 100)
    
    # Von unserem Anteil bekommen wir 15% Netto
    netto_betrag = unser_anteil_am_verkauf * 0.15
    
    # Berechne Brutto-Betrag (inkl. 19% MwSt)
    mwst = netto_betrag * 0.19
    gesamtbetrag = netto_betrag + mwst
    
    # Erstelle Rechnung
    rechnung = Rechnung(
        makler_id=lead.makler_id,
        rechnungstyp="beteiligung",
        lead_id=lead.id,
        verkaufspreis=verkaufspreis,
        beteiligungs_prozent=beteiligungs_prozent,
        netto_betrag=netto_betrag,
        gesamtbetrag=gesamtbetrag,
        status="offen",
        created_by_user_id=current_user.id
    )
    
    db.add(rechnung)
    db.commit()
    db.refresh(rechnung)
    
    return rechnung


@router.patch("/{rechnung_id}/status", response_model=schemas.RechnungRead)
def update_rechnung_status(
    rechnung_id: int,
    status_update: schemas.RechnungStatusUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_not_telefonist)
):
    """
    Aktualisiert den Status einer Rechnung (nur für Admin, Manager oder Buchhalter).
    Telefonist hat keinen Zugriff.
    """
    rechnung = db.query(Rechnung).filter(Rechnung.id == rechnung_id).first()
    if not rechnung:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Rechnung nicht gefunden"
        )
    
    rechnung.status = status_update.status
    db.commit()
    db.refresh(rechnung)
    
    return rechnung


@router.get("/{rechnung_id}/pdf")
def get_rechnung_pdf(
    rechnung_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_not_telefonist)
):
    """
    Generiert eine PDF-Rechnung für die angegebene Rechnung (nur für Admin, Manager oder Buchhalter).
    Telefonist hat keinen Zugriff.
    """
    rechnung = db.query(Rechnung).filter(Rechnung.id == rechnung_id).first()
    if not rechnung:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Rechnung nicht gefunden"
        )

    makler = db.query(Makler).filter(Makler.id == rechnung.makler_id).first()
    if not makler:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Makler nicht gefunden"
        )

    pdf_buffer = generiere_rechnung_pdf(rechnung, makler)
    
    # Generiere Dateinamen: namemakler.rechnungsnummer.pdf
    from ..services.pdf_service import generiere_rechnungsnummer
    import re
    rechnungsnummer = generiere_rechnungsnummer(rechnung, makler)
    # Mache Firmenname dateisystem-sicher (entferne Sonderzeichen, ersetze Leerzeichen)
    makler_name = re.sub(r'[^\w\s-]', '', makler.firmenname).strip()
    makler_name = re.sub(r'[-\s]+', '_', makler_name)  # Ersetze Leerzeichen und Bindestriche durch Unterstriche
    filename = f"{makler_name}.{rechnungsnummer}.pdf"
    
    return Response(
        content=pdf_buffer.read(),
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"'
        },
    )


@router.get("/{rechnung_id}", response_model=schemas.RechnungRead)
def get_rechnung(
    rechnung_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_not_telefonist)
):
    """
    Gibt eine Rechnung zurück (nur für Admin, Manager oder Buchhalter).
    Telefonist hat keinen Zugriff.
    """
    rechnung = db.query(Rechnung).filter(Rechnung.id == rechnung_id).first()
    if not rechnung:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Rechnung nicht gefunden"
        )
    return rechnung


