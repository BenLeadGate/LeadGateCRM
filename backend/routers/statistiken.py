from typing import Dict, Any
from datetime import datetime
from sqlalchemy import func, extract, and_
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Makler, Lead, Rechnung, User
from ..services.auth_service import get_current_active_user
from ..services.abrechnung_service import ist_makler_in_monat_aktiv

router = APIRouter()


@router.get("/dashboard")
def get_dashboard_stats(
    trends_start_monat: int = Query(None, ge=1, le=12, alias="trendsStartMonat"),
    trends_start_jahr: int = Query(None, alias="trendsStartJahr"),
    trends_anzahl_monate: int = Query(12, ge=1, le=24, alias="trendsAnzahlMonate"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
) -> Dict[str, Any]:
    """
    Liefert erweiterte Dashboard-Statistiken.
    """
    try:
        # Aktuelles Datum zuerst definieren
        jetzt = datetime.now()
        from sqlalchemy import or_
        
        # Basis-Statistiken (alle nur für aktuellen Monat)
        # OPTIMIERUNG: Zähle aktive Makler direkt in SQL statt alle zu laden
        # Aktive Makler sind nicht pausiert und Vertrag nicht abgelaufen
        # Für den aktuellen Monat: Nur Makler, die im aktuellen Monat aktiv sind
        aktive_makler_query = db.query(Makler.id).filter(
            or_(
                Makler.vertrag_pausiert == 0,
                Makler.vertrag_pausiert.is_(None)
            ),
            or_(
                Makler.vertrag_bis.is_(None),
                Makler.vertrag_bis >= datetime(jetzt.year, jetzt.month, 1).date()
            )
        )
        # Prüfe zusätzlich, ob Makler im aktuellen Monat aktiv ist (mit ist_makler_in_monat_aktiv)
        aktive_makler_ids_list = [m[0] for m in aktive_makler_query.all()]
        aktive_makler_ids = []
        for makler_id in aktive_makler_ids_list:
            makler = db.query(Makler).filter(Makler.id == makler_id).first()
            if makler and ist_makler_in_monat_aktiv(makler, jetzt.month, jetzt.year, db):
                aktive_makler_ids.append(makler_id)
        
        anzahl_makler = len(aktive_makler_ids)
        
        # Qualifizierte Leads nur für aktuellen Monat
        anzahl_gelieferte_leads = db.query(Lead).filter(
            or_(Lead.status == "qualifiziert", Lead.status == "flexrecall"),
            Lead.makler_id.in_(aktive_makler_ids) if aktive_makler_ids else Lead.makler_id.isnot(None),
            Lead.qualifiziert_am.isnot(None),
            extract("month", Lead.qualifiziert_am) == jetzt.month,
            extract("year", Lead.qualifiziert_am) == jetzt.year,
        ).count()
        
        # Rechnungen nur für aktuellen Monat
        anzahl_rechnungen = db.query(Rechnung).filter(
            or_(
                # Monatliche Rechnungen: Filter nach Monat und Jahr
                and_(
                    Rechnung.monat == jetzt.month,
                    Rechnung.jahr == jetzt.year
                ),
                # Beteiligungsrechnungen: Filter nach erstellt_am im aktuellen Monat
                and_(
                    Rechnung.rechnungstyp == "beteiligung",
                    extract("month", Rechnung.erstellt_am) == jetzt.month,
                    extract("year", Rechnung.erstellt_am) == jetzt.year
                )
            )
        ).count()
        
        # Umsatz-Statistiken (nur für aktuellen Monat)
        # Berücksichtigt sowohl monatliche Rechnungen (mit monat/jahr) als auch Beteiligungsrechnungen (mit erstellt_am)
        from sqlalchemy import or_
        gesamtumsatz_result = db.query(func.sum(Rechnung.gesamtbetrag)).filter(
            or_(
                # Monatliche Rechnungen: Filter nach Monat und Jahr
                and_(
                    Rechnung.monat == jetzt.month,
                    Rechnung.jahr == jetzt.year
                ),
                # Beteiligungsrechnungen: Filter nach erstellt_am im aktuellen Monat
                and_(
                    Rechnung.rechnungstyp == "beteiligung",
                    extract("month", Rechnung.erstellt_am) == jetzt.month,
                    extract("year", Rechnung.erstellt_am) == jetzt.year
                )
            )
        ).scalar()
        gesamtumsatz = float(gesamtumsatz_result) if gesamtumsatz_result is not None else 0.0
        
        # Anzahl Rechnungen im aktuellen Monat für Durchschnitt
        anzahl_rechnungen_dieser_monat = db.query(Rechnung).filter(
            or_(
                # Monatliche Rechnungen: Filter nach Monat und Jahr
                and_(
                    Rechnung.monat == jetzt.month,
                    Rechnung.jahr == jetzt.year
                ),
                # Beteiligungsrechnungen: Filter nach erstellt_am im aktuellen Monat
                and_(
                    Rechnung.rechnungstyp == "beteiligung",
                    extract("month", Rechnung.erstellt_am) == jetzt.month,
                    extract("year", Rechnung.erstellt_am) == jetzt.year
                )
            )
        ).count()
        
        durchschnittlicher_umsatz_pro_rechnung = (
            gesamtumsatz / anzahl_rechnungen_dieser_monat if anzahl_rechnungen_dieser_monat > 0 else 0.0
        )
        
        # Alle Leads dieses Monat (erstellt_am, nicht qualifiziert_am)
        leads_dieser_monat = (
            db.query(Lead)
            .filter(
                extract("month", Lead.erstellt_am) == jetzt.month,
                extract("year", Lead.erstellt_am) == jetzt.year,
            )
            .count()
        )
        
        # Top-Makler nach gelieferten Leads - nur aktive Makler berücksichtigen
        try:
            alle_makler = db.query(Makler).all()
            makler_stats = []
            for makler in alle_makler:
                # Prüfe, ob Makler aktiv ist (für Abrechnungszwecke)
                if not ist_makler_in_monat_aktiv(makler, jetzt.month, jetzt.year, db):
                    continue
                
                # Zähle gelieferte Leads dieses Maklers (nur qualifizierte/flexrecall)
                anzahl = db.query(Lead).filter(
                    Lead.makler_id == makler.id,
                    or_(Lead.status == "qualifiziert", Lead.status == "flexrecall")
                ).count()
                
                if anzahl > 0:
                    makler_stats.append({
                        "id": makler.id,
                        "firmenname": makler.firmenname,
                        "anzahl_leads": anzahl
                    })
            
            # Sortiere nach Anzahl Leads (absteigend) und nehme Top 4
            makler_stats.sort(key=lambda x: x["anzahl_leads"], reverse=True)
            top_makler = makler_stats[:4]
        except Exception as e:
            # Falls Fehler, leere Liste zurückgeben
            print(f"Warnung beim Laden der Top-Makler: {e}")
            top_makler = []
        
        # Monatliche Trends (mit Filter-Unterstützung)
        monatliche_trends = []
        
        # Bestimme Start-Monat und -Jahr basierend auf Parametern oder Standard (letzte 6 Monate)
        filter_aktiv = trends_start_monat is not None and trends_start_jahr is not None
        
        if filter_aktiv:
            # Mit Filter: Von Start-Monat vorwärts (alt zu neu)
            start_monat = trends_start_monat
            start_jahr = trends_start_jahr
            anzahl_monate = trends_anzahl_monate
            
            # Berechne alle Monate vorwärts vom Start-Monat
            for i in range(anzahl_monate):
                monat = start_monat + i
                jahr = start_jahr
                
                # Berechne korrektes Jahr/Monat wenn Monat > 12
                while monat > 12:
                    monat -= 12
                    jahr += 1
                
                try:
                    # Zähle qualifizierte/flexrecall-Leads, die im jeweiligen Monat qualifiziert wurden
                    # Nur von aktiven Maklern
                    leads_query = db.query(Lead).filter(
                        or_(Lead.status == "qualifiziert", Lead.status == "flexrecall"),
                        Lead.makler_id.isnot(None),
                        Lead.qualifiziert_am.isnot(None),
                        extract("month", Lead.qualifiziert_am) == monat,
                        extract("year", Lead.qualifiziert_am) == jahr,
                    ).all()
                    
                    anzahl = 0
                    for lead in leads_query:
                        makler = db.query(Makler).filter(Makler.id == lead.makler_id).first()
                        if makler and ist_makler_in_monat_aktiv(makler, monat, jahr, db):
                            anzahl += 1
                    
                    monatliche_trends.append({"monat": monat, "jahr": jahr, "anzahl": anzahl})
                except Exception as e:
                    print(f"Warnung beim Laden der Trends für {monat}/{jahr}: {e}")
                    monatliche_trends.append({"monat": monat, "jahr": jahr, "anzahl": 0})
        else:
            # Ohne Filter: Von aktuellen Monat rückwärts (neu zu alt)
            anzahl_monate = 6
            
            # Berechne alle Monate rückwärts vom aktuellen Monat
            for i in range(anzahl_monate):
                monat = jetzt.month - i
                jahr = jetzt.year
                
                # Berechne korrektes Jahr/Monat wenn Monat <= 0
                while monat <= 0:
                    monat += 12
                    jahr -= 1
                
                try:
                    # Zähle qualifizierte/flexrecall-Leads, die im jeweiligen Monat qualifiziert wurden
                    # Nur von aktiven Maklern
                    leads_query = db.query(Lead).filter(
                        or_(Lead.status == "qualifiziert", Lead.status == "flexrecall"),
                        Lead.makler_id.isnot(None),
                        Lead.qualifiziert_am.isnot(None),
                        extract("month", Lead.qualifiziert_am) == monat,
                        extract("year", Lead.qualifiziert_am) == jahr,
                    ).all()
                    
                    anzahl = 0
                    for lead in leads_query:
                        makler = db.query(Makler).filter(Makler.id == lead.makler_id).first()
                        if makler and ist_makler_in_monat_aktiv(makler, monat, jahr, db):
                            anzahl += 1
                    
                    monatliche_trends.append({"monat": monat, "jahr": jahr, "anzahl": anzahl})
                except Exception as e:
                    print(f"Warnung beim Laden der Trends für {monat}/{jahr}: {e}")
                    monatliche_trends.append({"monat": monat, "jahr": jahr, "anzahl": 0})
        
        return {
            "basis": {
                "anzahl_makler": anzahl_makler,
                "anzahl_gelieferte_leads": anzahl_gelieferte_leads,
                "anzahl_rechnungen": anzahl_rechnungen,
            },
            "umsatz": {
                "gesamtumsatz": gesamtumsatz,
                "durchschnitt_pro_rechnung": float(durchschnittlicher_umsatz_pro_rechnung),
            },
            "aktueller_monat": {
                "leads": leads_dieser_monat,
                "gelieferte_leads": anzahl_gelieferte_leads,
            },
            "top_makler": top_makler,
            "monatliche_trends": monatliche_trends,
        }
    except Exception as e:
        import traceback
        error_msg = f"Fehler beim Laden der Dashboard-Statistiken: {str(e)}"
        print(error_msg)
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=error_msg)


@router.get("/qualifizierungen-pro-user")
def get_qualifizierungen_pro_user(
    monat: int = Query(None, ge=1, le=12),
    jahr: int = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
) -> Dict[str, Any]:
    """
    Liefert eine Übersicht, welcher User wie viele Leads pro Monat qualifiziert hat.
    Nur für Admin und Manager verfügbar.
    """
    from ..models.user import UserRole
    
    # Prüfe Berechtigung
    if current_user.role not in [UserRole.ADMIN, UserRole.MANAGER]:
        raise HTTPException(status_code=403, detail="Nur für Admin und Manager verfügbar")
    
    jetzt = datetime.now()
    if monat is None:
        monat = jetzt.month
    if jahr is None:
        jahr = jetzt.year
    
    # Lade alle qualifizierten und flexrecall-Leads im angegebenen Monat (nicht reklamiert)
    from sqlalchemy import or_
    qualifizierte_leads = (
        db.query(Lead)
        .filter(
            or_(Lead.status == "qualifiziert", Lead.status == "flexrecall"),
            Lead.qualifiziert_von_user_id.isnot(None),
            Lead.qualifiziert_am.isnot(None),
            extract("month", Lead.qualifiziert_am) == monat,
            extract("year", Lead.qualifiziert_am) == jahr,
        )
        .all()
    )
    
    # Gruppiere nach qualifiziert_von_user_id
    user_qualifizierungen = {}
    for lead in qualifizierte_leads:
        user_id = lead.qualifiziert_von_user_id
        if user_id not in user_qualifizierungen:
            # Lade User-Details
            user = db.query(User).filter(User.id == user_id).first()
            user_qualifizierungen[user_id] = {
                "user_id": user_id,
                "username": user.username if user else "Unbekannt",
                "anzahl": 0
            }
        user_qualifizierungen[user_id]["anzahl"] += 1
    
    # Konvertiere zu Liste und sortiere nach Anzahl (absteigend)
    result = list(user_qualifizierungen.values())
    result.sort(key=lambda x: x["anzahl"], reverse=True)
    
    return {
        "monat": monat,
        "jahr": jahr,
        "qualifizierungen": result,
        "gesamt": sum(u["anzahl"] for u in result)
    }

