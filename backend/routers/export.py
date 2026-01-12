from fastapi import APIRouter, Depends
from fastapi.responses import Response
from sqlalchemy.orm import Session
import csv
from io import StringIO

from ..database import get_db
from ..models import Makler, Lead, Rechnung, User
from ..services.auth_service import get_current_active_user

router = APIRouter()


@router.get("/makler/csv")
def export_makler_csv(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Exportiert alle Makler als CSV.
    """
    makler = db.query(Makler).all()
    
    output = StringIO()
    writer = csv.writer(output)
    
    # Header
    writer.writerow([
        "ID", "Firmenname", "Ansprechpartner", "Email", "Adresse",
        "Vertragsstart", "Testphase Leads", "Testphase Preis", "Standard Preis"
    ])
    
    # Daten
    for m in makler:
        writer.writerow([
            m.id, m.firmenname, m.ansprechpartner or "", m.email, m.adresse or "",
            m.vertragsstart_datum, m.testphase_leads, m.testphase_preis, m.standard_preis
        ])
    
    output.seek(0)
    return Response(
        content=output.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=makler_export.csv"}
    )


@router.get("/leads/csv")
def export_leads_csv(db: Session = Depends(get_db)):
    """
    Exportiert alle Leads als CSV.
    """
    leads = db.query(Lead).all()
    
    output = StringIO()
    writer = csv.writer(output)
    
    # Header
    writer.writerow(["ID", "Makler ID", "Status", "Erstellt am"])
    
    # Daten
    for l in leads:
        writer.writerow([
            l.id, l.makler_id, l.status, l.erstellt_am.isoformat() if l.erstellt_am else ""
        ])
    
    output.seek(0)
    return Response(
        content=output.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=leads_export.csv"}
    )


@router.get("/rechnungen/csv")
def export_rechnungen_csv(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Exportiert alle Rechnungen als CSV.
    """
    rechnungen = db.query(Rechnung).all()
    
    output = StringIO()
    writer = csv.writer(output)
    
    # Header
    writer.writerow([
        "ID", "Makler ID", "Monat", "Jahr", "Anzahl Leads",
        "Preis pro Lead", "Gesamtbetrag", "Erstellt am"
    ])
    
    # Daten
    for r in rechnungen:
        writer.writerow([
            r.id, r.makler_id, r.monat, r.jahr, r.anzahl_leads,
            r.preis_pro_lead, r.gesamtbetrag,
            r.erstellt_am.isoformat() if r.erstellt_am else ""
        ])
    
    output.seek(0)
    return Response(
        content=output.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=rechnungen_export.csv"}
    )


