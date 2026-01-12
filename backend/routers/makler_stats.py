from typing import List, Dict, Any
from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Makler, Lead, User
from ..services.auth_service import get_current_active_user

router = APIRouter()


@router.get("/mit-statistiken")
def get_makler_mit_statistiken(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
) -> List[Dict[str, Any]]:
    """
    Liefert alle Makler mit Lead-Statistiken.
    """
    makler_list = db.query(Makler).all()
    result = []
    
    for makler in makler_list:
        # Lead-Statistiken pro Makler
        anzahl_leads_gesamt = db.query(Lead).filter(Lead.makler_id == makler.id).count()
        anzahl_leads_geliefert = db.query(Lead).filter(
            Lead.makler_id == makler.id,
            Lead.status == "geliefert"
        ).count()
        anzahl_leads_neu = db.query(Lead).filter(
            Lead.makler_id == makler.id,
            Lead.status == "neu"
        ).count()
        anzahl_leads_storniert = db.query(Lead).filter(
            Lead.makler_id == makler.id,
            Lead.status == "storniert"
        ).count()
        
        result.append({
            "id": makler.id,
            "firmenname": makler.firmenname,
            "ansprechpartner": makler.ansprechpartner,
            "email": makler.email,
            "adresse": makler.adresse,
            "vertragsstart_datum": makler.vertragsstart_datum.isoformat(),
            "testphase_leads": makler.testphase_leads,
            "testphase_preis": makler.testphase_preis,
            "standard_preis": makler.standard_preis,
            "monatliche_soll_leads": makler.monatliche_soll_leads,
            "statistiken": {
                "leads_gesamt": anzahl_leads_gesamt,
                "leads_geliefert": anzahl_leads_geliefert,
                "leads_neu": anzahl_leads_neu,
                "leads_storniert": anzahl_leads_storniert,
            }
        })
    
    return result

