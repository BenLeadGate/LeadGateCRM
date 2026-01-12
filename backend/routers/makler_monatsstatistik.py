from typing import List, Dict, Any
from datetime import datetime, date
from sqlalchemy import extract, func
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Makler, Lead, User
from ..services.abrechnung_service import berechne_vertragsmonat, bestimme_preis_pro_lead, ist_makler_in_monat_aktiv
from ..services.auth_service import get_current_active_user

router = APIRouter()


@router.get("/monatsstatistik")
def get_makler_monatsstatistik(
    monat: int = Query(None, ge=1, le=12),
    jahr: int = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
) -> List[Dict[str, Any]]:
    """
    Liefert für alle Makler die Soll/Ist-Lead-Statistik für einen Monat inkl. Geld-Berechnungen.
    """
    import logging
    try:
        jetzt = datetime.now()
        if monat is None:
            monat = jetzt.month
        if jahr is None:
            jahr = jetzt.year
        
        makler_list = db.query(Makler).all()
        result = []
        
        for makler in makler_list:
            try:
                # Prüfe, ob Makler im Abrechnungsmonat aktiv ist (für Abrechnungszwecke)
                # WICHTIG: Bereits gelieferte Leads werden berücksichtigt, auch wenn pausiert
                ist_aktiv = ist_makler_in_monat_aktiv(makler, monat, jahr, db)
                
                # Berechne Vertragsmonat
                if makler.vertragsstart_datum:
                    vertragsmonat = berechne_vertragsmonat(makler.vertragsstart_datum, monat, jahr)
                else:
                    vertragsmonat = 1  # Fallback wenn kein Vertragsstart-Datum
                
                # Prüfe ob Makler pausiert ist
                ist_pausiert = False
                if makler.vertrag_pausiert == 1:
                    jetzt = datetime.now()
                    monats_datum = date(jahr, monat, 1)
                    aktueller_monat_datum = date(jetzt.year, jetzt.month, 1)
                    if monats_datum >= aktueller_monat_datum:
                        ist_pausiert = True
                
                # Soll: Priorität: monatliche_soll_leads > testphase_leads (nur Monat 1) > None
                # WICHTIG: Wenn Makler pausiert ist, werden Soll-Leads trotzdem angezeigt (für die Anzeige)
                # Wenn Makler nicht aktiv ist (und nicht pausiert), gibt es keine Soll-Leads
                if ist_pausiert:
                    # Wenn pausiert, zeige trotzdem Soll-Leads an (für die Anzeige)
                    if makler.monatliche_soll_leads is not None:
                        soll_leads = makler.monatliche_soll_leads
                    elif vertragsmonat == 1 and makler.testphase_leads and makler.testphase_leads > 0:
                        soll_leads = makler.testphase_leads
                    else:
                        soll_leads = None  # None = unbegrenzt
                elif not ist_aktiv:
                    soll_leads = None  # Keine Soll-Leads, wenn Makler nicht aktiv ist
                elif makler.monatliche_soll_leads is not None:
                    soll_leads = makler.monatliche_soll_leads
                elif vertragsmonat == 1 and makler.testphase_leads and makler.testphase_leads > 0:
                    soll_leads = makler.testphase_leads
                else:
                    soll_leads = None  # None = unbegrenzt
                
                # Ist: Qualifizierte Leads im Monat (nur Leads mit Status "qualifiziert" und qualifiziert_am im Monat)
                # WICHTIG: Bereits gelieferte Leads werden immer gezählt, auch wenn pausiert
                # (ist_aktiv berücksichtigt bereits gelieferte Leads, daher können wir immer zählen)
                ist_leads = (
                    db.query(Lead)
                    .filter(
                        Lead.makler_id == makler.id,
                        Lead.status == "qualifiziert",
                        Lead.qualifiziert_am.isnot(None),
                        extract("month", Lead.qualifiziert_am) == monat,
                        extract("year", Lead.qualifiziert_am) == jahr,
                    )
                    .count()
                )
                
                # Preis pro Lead berechnen
                preis_pro_lead = bestimme_preis_pro_lead(makler, vertragsmonat)
                
                # Geld-Berechnungen
                ist_geld = ist_leads * preis_pro_lead
                
                # Potenzial: Wenn Soll definiert ist, berechne fehlende Leads * Preis
                if soll_leads is not None and soll_leads > ist_leads:
                    fehlende_leads = soll_leads - ist_leads
                    potenzial_geld = fehlende_leads * preis_pro_lead
                else:
                    potenzial_geld = 0.0
                
                # Soll-Geld: Wenn Soll definiert ist
                soll_geld = soll_leads * preis_pro_lead if soll_leads is not None else None
                
                # Berechne Lieferung in Prozent
                lieferung_prozent = None
                if soll_leads and soll_leads > 0:
                    if ist_pausiert:
                        # Wenn pausiert, setze auf 100%
                        lieferung_prozent = 100.0
                    else:
                        lieferung_prozent = (ist_leads / soll_leads * 100) if soll_leads > 0 else 0.0
                
                result.append({
                    "makler_id": makler.id,
                    "firmenname": makler.firmenname,
                    "vertragsmonat": vertragsmonat,
                    "soll_leads": soll_leads,
                    "ist_leads": ist_leads,
                    "preis_pro_lead": preis_pro_lead,
                    "ist_geld": ist_geld,
                    "soll_geld": soll_geld,
                    "potenzial_geld": potenzial_geld,
                    "ist_aktiv": ist_aktiv,  # Hinzufügen des Aktiv-Status
                    "ist_pausiert": ist_pausiert,  # Hinzufügen des Pausiert-Status
                    "lieferung_prozent": lieferung_prozent,  # Lieferung in Prozent
                    "monat": monat,
                    "jahr": jahr,
                })
            except Exception as e:
                logging.error(f"Fehler bei Verarbeitung von Makler {makler.id} in Monatsstatistik: {str(e)}", exc_info=True)
                # Überspringe diesen Makler bei Fehler
                continue
        
        return result
    except Exception as e:
        logging.error(f"Kritischer Fehler in get_makler_monatsstatistik: {str(e)}", exc_info=True)
        from fastapi import HTTPException, status
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Fehler beim Laden der Monatsstatistik: {str(e)}"
        )

