"""
Service für die Organisations- und Koordinationslogik.
Berechnet Verfügbarkeit, Priorität und Status für Makler.
"""

from datetime import datetime, date
from typing import Dict, Any, List, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import extract, func

from ..models import Makler, Lead, MaklerCredits
from .credits_service import (
    berechne_credits_stand,
    berechne_preis_fuer_lead,
    zaehle_leads_im_monat
)
from .abrechnung_service import (
    ist_makler_in_monat_aktiv,
    berechne_vertragsmonat,
    bestimme_preis_pro_lead,
    kann_makler_neue_leads_bekommen
)


def berechne_durchschnittlichen_preis(
    db: Session,
    makler: Makler,
    monat: int,
    jahr: int
) -> float:
    """
    Berechnet den durchschnittlichen Preis für Leads eines Maklers in einem Monat.
    Berücksichtigt die Preislogik (erste X Leads günstiger, danach teurer).
    
    Args:
        db: Datenbank-Session
        makler: Der Makler
        monat: Monat (1-12)
        jahr: Jahr
    
    Returns:
        Durchschnittlicher Preis pro Lead in Euro
    """
    # Zähle Leads im Monat
    anzahl_leads = zaehle_leads_im_monat(db, makler.id, monat, jahr)
    
    if anzahl_leads == 0:
        # Keine Leads bisher: Verwende erwarteten Preis für ersten Lead
        vertragsmonat = berechne_vertragsmonat(makler.vertragsstart_datum, monat, jahr)
        if vertragsmonat == 1:
            # Erster Monat: Erster Lead kostet erste_leads_preis
            return makler.erste_leads_preis if makler.erste_leads_preis is not None else 50.0
        else:
            # Ab 2. Monat: Standard-Preis
            return makler.standard_preis if makler.standard_preis is not None else 100.0
    
    # Berechne Gesamtpreis für alle Leads im Monat
    vertragsmonat = berechne_vertragsmonat(makler.vertragsstart_datum, monat, jahr)
    gesamtpreis = 0.0
    
    erste_leads_anzahl = makler.erste_leads_anzahl if makler.erste_leads_anzahl is not None else 5
    erste_leads_preis = makler.erste_leads_preis if makler.erste_leads_preis is not None else 50.0
    erste_leads_danach_preis = makler.erste_leads_danach_preis if makler.erste_leads_danach_preis is not None else 75.0
    standard_preis = makler.standard_preis if makler.standard_preis is not None else 100.0
    
    if vertragsmonat == 1:
        # Erster Monat: Erste X Leads = erste_leads_preis, danach = erste_leads_danach_preis
        for i in range(1, anzahl_leads + 1):
            if i <= erste_leads_anzahl:
                gesamtpreis += erste_leads_preis
            else:
                gesamtpreis += erste_leads_danach_preis
    else:
        # Ab 2. Monat: Standard-Preis
        gesamtpreis = anzahl_leads * standard_preis
    
    return gesamtpreis / anzahl_leads if anzahl_leads > 0 else standard_preis


def berechne_verfuegbare_leads_aus_credits(
    db: Session,
    makler: Makler,
    monat: int,
    jahr: int
) -> Tuple[int, float, float]:
    """
    Berechnet wie viele Leads ein Makler mit Credits-System noch bekommen kann.
    
    Args:
        db: Datenbank-Session
        makler: Der Makler (muss rechnungssystem_typ = "neu" haben)
        monat: Monat (1-12)
        jahr: Jahr
    
    Returns:
        Tuple (verfuegbare_leads: int, durchschnittlicher_preis: float, naechster_lead_preis: float)
    """
    if makler.rechnungssystem_typ != "neu":
        return 0, 0.0, 0.0
    
    credits_stand = berechne_credits_stand(db, makler.id)
    
    # Berechne durchschnittlichen Preis basierend auf bisherigen Leads
    durchschnittlicher_preis = berechne_durchschnittlichen_preis(db, makler, monat, jahr)
    
    # Berechne Preis für nächsten Lead
    anzahl_leads_aktuell = zaehle_leads_im_monat(db, makler.id, monat, jahr)
    vertragsmonat = berechne_vertragsmonat(makler.vertragsstart_datum, monat, jahr)
    
    # Simuliere nächsten Lead für Preisberechnung
    test_datum = datetime(jahr, monat, 15, 12, 0, 0)
    naechster_lead_preis = berechne_preis_fuer_lead(makler, test_datum, anzahl_leads_aktuell + 1)
    
    # Verfügbare Leads = Credits / Durchschnittlicher Preis (konservativ)
    # Verwende den höheren Wert zwischen Durchschnitt und nächstem Lead-Preis für Sicherheit
    sicherheits_preis = max(durchschnittlicher_preis, naechster_lead_preis)
    verfuegbare_leads = int(credits_stand / sicherheits_preis) if sicherheits_preis > 0 else 0
    
    return verfuegbare_leads, durchschnittlicher_preis, naechster_lead_preis


def berechne_makler_status(
    db: Session,
    makler: Makler,
    monat: int,
    jahr: int
) -> Dict[str, Any]:
    """
    Berechnet den Status und die Verfügbarkeit eines Maklers.
    
    Args:
        db: Datenbank-Session
        makler: Der Makler
        monat: Monat (1-12)
        jahr: Jahr
    
    Returns:
        Dict mit Status-Informationen
    """
    # Prüfe ob Makler aktiv ist (für Abrechnungszwecke - bereits gelieferte Leads werden berücksichtigt)
    ist_aktiv = ist_makler_in_monat_aktiv(makler, monat, jahr, db)
    
    # Prüfe ob Makler neue Leads bekommen kann (für Lead-Zuweisungen)
    kann_neue_leads = kann_makler_neue_leads_bekommen(makler, monat, jahr)
    
    # Prüfe ob Makler pausiert ist
    from datetime import datetime
    ist_pausiert = False
    if makler.vertrag_pausiert == 1:
        jetzt = datetime.now()
        monats_datum = date(jahr, monat, 1)
        aktueller_monat_datum = date(jetzt.year, jetzt.month, 1)
        if monats_datum >= aktueller_monat_datum:
            ist_pausiert = True
    
    # Wenn pausiert, setze Status auf "pausiert" und Lead-Lieferung auf 100%
    if ist_pausiert:
        ist_leads = zaehle_leads_im_monat(db, makler.id, monat, jahr)
        # Berechne Soll-Leads für Anzeige
        vertragsmonat = berechne_vertragsmonat(makler.vertragsstart_datum, monat, jahr)
        if makler.monatliche_soll_leads is not None:
            soll_leads = makler.monatliche_soll_leads
        elif vertragsmonat == 1 and makler.testphase_leads and makler.testphase_leads > 0:
            soll_leads = makler.testphase_leads
        else:
            soll_leads = None
        
        return {
            "status": "pausiert",
            "prioritaet": "niedrig",
            "kann_leads": False,
            "ist_leads": ist_leads,
            "soll_leads": soll_leads,
            "fehlend_leads": 0,  # Keine fehlenden Leads, da pausiert
            "noch_benoetigt": 0,  # Keine neuen Leads benötigt, da pausiert
            "lieferung_prozent": 100.0 if soll_leads and soll_leads > 0 else None,  # Auf 100% setzen
            "warnung": "Vertrag ist pausiert - keine neuen Leads werden zugewiesen"
        }
    
    if not ist_aktiv:
        ist_leads = zaehle_leads_im_monat(db, makler.id, monat, jahr)
        return {
            "status": "inaktiv",
            "prioritaet": "niedrig",
            "kann_leads": False,
            "ist_leads": ist_leads,
            "lieferung_prozent": None,
            "warnung": "Makler ist inaktiv (Vertrag abgelaufen)"
        }
    
    ist_leads = zaehle_leads_im_monat(db, makler.id, monat, jahr) if ist_aktiv else 0
    
    # Sicherstellen, dass rechnungssystem_typ nicht None ist (Default: "alt")
    rechnungssystem_typ = makler.rechnungssystem_typ if makler.rechnungssystem_typ else "alt"
    
    # Altes System
    if rechnungssystem_typ == "alt":
        vertragsmonat = berechne_vertragsmonat(makler.vertragsstart_datum, monat, jahr)
        
        # Soll-Leads bestimmen
        if makler.monatliche_soll_leads is not None:
            soll_leads = makler.monatliche_soll_leads
        elif vertragsmonat == 1 and makler.testphase_leads > 0:
            soll_leads = makler.testphase_leads
        else:
            soll_leads = None  # Unbegrenzt
        
        if soll_leads is None:
            # Unbegrenzt: Kann immer Leads bekommen (wenn nicht pausiert)
            return {
                "status": "kann_leads",
                "prioritaet": "normal",
                "kann_leads": kann_neue_leads,  # Kann nur Leads bekommen, wenn nicht pausiert
                "ist_leads": ist_leads,
                "soll_leads": None,
                "fehlend_leads": None,
                "lieferung_prozent": None,  # Keine Prozentangabe bei unbegrenzt
                "warnung": None
            }
        else:
            fehlend_leads = max(0, soll_leads - ist_leads)
            lieferung_prozent = (ist_leads / soll_leads * 100) if soll_leads > 0 else 0.0
            
            if fehlend_leads > 0:
                # Noch Leads benötigt
                prioritaet = "hoch" if fehlend_leads >= 3 else "normal"
                return {
                    "status": "kann_leads",
                    "prioritaet": prioritaet,
                    "kann_leads": kann_neue_leads,  # Kann nur Leads bekommen, wenn nicht pausiert
                    "ist_leads": ist_leads,
                    "soll_leads": soll_leads,
                    "fehlend_leads": fehlend_leads,
                    "lieferung_prozent": lieferung_prozent,
                    "warnung": None
                }
            else:
                # Voll
                return {
                    "status": "voll",
                    "prioritaet": "niedrig",
                    "kann_leads": False,
                    "ist_leads": ist_leads,
                    "soll_leads": soll_leads,
                    "fehlend_leads": 0,
                    "lieferung_prozent": 100.0,  # 100% erreicht
                    "warnung": "Soll-Leads erreicht"
                }
    
    # Neues System (Credits)
    elif rechnungssystem_typ == "neu":
        credits_stand = berechne_credits_stand(db, makler.id)
        verfuegbare_leads, durchschnittlicher_preis, naechster_lead_preis = berechne_verfuegbare_leads_aus_credits(
            db, makler, monat, jahr
        )
        
        if credits_stand < naechster_lead_preis:
            # Keine Credits für nächsten Lead
            return {
                "status": "keine_credits",
                "prioritaet": "niedrig",
                "kann_leads": False,  # Kann keine Leads bekommen, wenn keine Credits (kann_neue_leads wird bereits in der Prüfung berücksichtigt)
                "credits_stand": credits_stand,
                "verfuegbare_leads": 0,
                "durchschnittlicher_preis": durchschnittlicher_preis,
                "naechster_lead_preis": naechster_lead_preis,
                "ist_leads": ist_leads,
                "warnung": f"Nicht genug Credits. Benötigt: {naechster_lead_preis:.2f}€, Vorhanden: {credits_stand:.2f}€"
            }
        elif credits_stand < (naechster_lead_preis * 3):
            # Wenig Credits (Warnung)
            return {
                "status": "wenig_credits",
                "prioritaet": "hoch",
                "kann_leads": kann_neue_leads,  # Kann nur Leads bekommen, wenn nicht pausiert
                "credits_stand": credits_stand,
                "verfuegbare_leads": verfuegbare_leads,
                "durchschnittlicher_preis": durchschnittlicher_preis,
                "naechster_lead_preis": naechster_lead_preis,
                "ist_leads": ist_leads,
                "warnung": f"Wenig Credits: {credits_stand:.2f}€ (~{verfuegbare_leads} Leads verfügbar)"
            }
        else:
            # Genug Credits
            prioritaet = "normal" if verfuegbare_leads >= 5 else "hoch"
            return {
                "status": "kann_leads",
                "prioritaet": prioritaet,
                "kann_leads": kann_neue_leads,  # Kann nur Leads bekommen, wenn nicht pausiert
                "credits_stand": credits_stand,
                "verfuegbare_leads": verfuegbare_leads,
                "durchschnittlicher_preis": durchschnittlicher_preis,
                "naechster_lead_preis": naechster_lead_preis,
                "ist_leads": ist_leads,
                "warnung": None
            }
    else:
        # Fallback für unbekannte System-Typen
        return {
            "status": "inaktiv",
            "prioritaet": "niedrig",
            "kann_leads": False,
            "ist_leads": ist_leads,
            "warnung": f"Unbekanntes Rechnungssystem: {rechnungssystem_typ}"
        }


def get_telefonist_dashboard(
    db: Session,
    filter_status: Optional[str] = None,  # "kann_leads", "wenig_credits", "voll", "keine_credits"
    filter_system: Optional[str] = None,  # "alt", "neu"
    suche: Optional[str] = None  # Suche nach Firmenname oder PLZ
) -> Dict[str, Any]:
    """
    Hauptfunktion für das Telefonist-Dashboard.
    Gibt eine Liste aller Makler mit Status-Informationen zurück.
    
    Args:
        db: Datenbank-Session
        filter_status: Optionaler Filter nach Status
        filter_system: Optionaler Filter nach Rechnungssystem
        suche: Optionaler Suchbegriff (Firmenname oder PLZ)
    
    Returns:
        Dict mit makler_liste und statistiken
    """
    jetzt = datetime.now()
    aktueller_monat = jetzt.month
    aktuelles_jahr = jetzt.year
    
    # Hole alle Makler
    makler_query = db.query(Makler)
    
    # Filter nach Suche
    if suche:
        suche_lower = suche.lower()
        makler_query = makler_query.filter(
            (Makler.firmenname.ilike(f"%{suche}%")) |
            (Makler.gebiet.ilike(f"%{suche}%"))
        )
    
    alle_makler = makler_query.all()
    
    makler_liste = []
    statistiken = {
        "gesamt_makler": 0,
        "kann_leads": 0,
        "wenig_credits": 0,
        "voll": 0,
        "keine_credits": 0,
        "inaktiv": 0,
        "pausiert": 0
    }
    
    for makler in alle_makler:
        status_info = berechne_makler_status(db, makler, aktueller_monat, aktuelles_jahr)
        
        # Pausierte Makler werden nicht im Dashboard angezeigt (sie brauchen keine neuen Leads)
        if status_info["status"] == "pausiert":
            # Zähle sie in den Statistiken, aber zeige sie nicht in der Liste
            statistiken["pausiert"] += 1
            continue
        
        # Filter anwenden
        if filter_status and status_info["status"] != filter_status:
            continue
        
        # Sicherstellen, dass rechnungssystem_typ nicht None ist (Default: "alt")
        rechnungssystem_typ = makler.rechnungssystem_typ if makler.rechnungssystem_typ else "alt"
        
        if filter_system and rechnungssystem_typ != filter_system:
            continue
        
        # Gebiet parsen
        gebiet_liste = []
        if makler.gebiet:
            gebiet_liste = [plz.strip() for plz in makler.gebiet.split(",") if plz.strip()]
        
        makler_daten = {
            "makler_id": makler.id,
            "firmenname": makler.firmenname,
            "gebiet": makler.gebiet or "",
            "gebiet_liste": gebiet_liste,
            "rechnungssystem_typ": rechnungssystem_typ,
            **status_info
        }
        
        makler_liste.append(makler_daten)
        
        # Statistiken aktualisieren
        statistiken["gesamt_makler"] += 1
        if status_info["status"] == "kann_leads":
            statistiken["kann_leads"] += 1
        elif status_info["status"] == "wenig_credits":
            statistiken["wenig_credits"] += 1
        elif status_info["status"] == "voll":
            statistiken["voll"] += 1
        elif status_info["status"] == "keine_credits":
            statistiken["keine_credits"] += 1
        elif status_info["status"] == "inaktiv":
            statistiken["inaktiv"] += 1
        # Pausierte Makler werden bereits vorher gezählt und aus der Liste ausgeschlossen
    
    # Sortiere nach Priorität
    prioritaet_ordnung = {"hoch": 1, "normal": 2, "niedrig": 3}
    makler_liste.sort(key=lambda x: (
        prioritaet_ordnung.get(x.get("prioritaet", "normal"), 2),
        -x.get("fehlend_leads", 0) if x.get("fehlend_leads") is not None else 0,
        -x.get("verfuegbare_leads", 0) if x.get("verfuegbare_leads") is not None else 0
    ))
    
    return {
        "makler_liste": makler_liste,
        "statistiken": statistiken,
        "aktueller_monat": aktueller_monat,
        "aktuelles_jahr": aktuelles_jahr
    }

