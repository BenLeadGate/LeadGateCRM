"""
API-Endpunkte für das Organisations- und Koordinationssystem.
"""

from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import User
from ..services.auth_service import get_current_active_user
from ..services.organisation_service import get_telefonist_dashboard, berechne_makler_status
from ..services.lead_empfehlung_service import get_lead_empfehlung_fuer_telefonist

router = APIRouter()


@router.get("/telefonist/dashboard")
def telefonist_dashboard(
    filter_status: Optional[str] = Query(None, description="Filter nach Status: kann_leads, wenig_credits, voll, keine_credits"),
    filter_system: Optional[str] = Query(None, description="Filter nach System: alt, neu"),
    suche: Optional[str] = Query(None, description="Suche nach Firmenname oder PLZ"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Gibt das Dashboard für Telefonisten zurück.
    Zeigt alle Makler mit Status, Verfügbarkeit und Priorität.
    """
    return get_telefonist_dashboard(
        db=db,
        filter_status=filter_status,
        filter_system=filter_system,
        suche=suche
    )


@router.get("/telefonist/makler/{makler_id}/verfuegbarkeit")
def makler_verfuegbarkeit(
    makler_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Gibt detaillierte Verfügbarkeits-Informationen für einen Makler zurück.
    """
    from datetime import datetime
    from ..models import Makler
    from fastapi import HTTPException, status
    
    makler = db.query(Makler).filter(Makler.id == makler_id).first()
    if not makler:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Makler nicht gefunden"
        )
    
    jetzt = datetime.now()
    status_info = berechne_makler_status(db, makler, jetzt.month, jetzt.year)
    
    # Gebiet parsen
    gebiet_liste = []
    if makler.gebiet:
        gebiet_liste = [plz.strip() for plz in makler.gebiet.split(",") if plz.strip()]
    
    return {
        "makler_id": makler.id,
        "firmenname": makler.firmenname,
        "gebiet": makler.gebiet or "",
        "gebiet_liste": gebiet_liste,
        "rechnungssystem_typ": makler.rechnungssystem_typ,
        **status_info
    }


@router.get("/telefonist/lead-empfehlung")
def telefonist_lead_empfehlung(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Gibt eine Lead-Empfehlung für den Telefonisten zurück.
    Zeigt, welchen Lead er als nächstes anrufen soll.
    Berücksichtigt Locking (verhindert, dass mehrere Telefonisten am selben Lead arbeiten).
    """
    return get_lead_empfehlung_fuer_telefonist(db, aktueller_user_id=current_user.id)

