"""
Service für die Lead-Empfehlung an Telefonisten.
Berechnet, welchen Lead ein Telefonist als nächstes anrufen soll.
"""

from datetime import datetime, date, timedelta
from typing import Dict, Any, List, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import extract, and_, or_

from ..models import Makler, Lead
from .organisation_service import berechne_makler_status
from .abrechnung_service import ist_makler_in_monat_aktiv, berechne_vertragsmonat, kann_makler_neue_leads_bekommen


def berechne_arbeitstage_bis_monatsende(aktuelles_datum: date) -> int:
    """
    Berechnet die Anzahl der Arbeitstage (Mo-Fr) bis zum Monatsende.
    
    Args:
        aktuelles_datum: Das aktuelle Datum
    
    Returns:
        Anzahl der Arbeitstage (ohne Wochenende)
    """
    # Letzter Tag des Monats
    if aktuelles_datum.month == 12:
        letzter_tag = date(aktuelles_datum.year + 1, 1, 1) - timedelta(days=1)
    else:
        letzter_tag = date(aktuelles_datum.year, aktuelles_datum.month + 1, 1) - timedelta(days=1)
    
    arbeitstage = 0
    aktueller_tag = aktuelles_datum
    
    while aktueller_tag <= letzter_tag:
        # 0 = Montag, 6 = Sonntag
        wochentag = aktueller_tag.weekday()
        if wochentag < 5:  # Montag bis Freitag
            arbeitstage += 1
        aktueller_tag += timedelta(days=1)
    
    return arbeitstage


def berechne_tagessatz_fuer_makler(
    db: Session,
    makler: Makler,
    monat: int,
    jahr: int,
    aktuelles_datum: date
) -> Dict[str, Any]:
    """
    Berechnet den Tagessatz (wie viele Leads muss dieser Makler heute noch bekommen)
    und die noch benötigten Leads für den Monat.
    
    Args:
        db: Datenbank-Session
        makler: Der Makler
        monat: Monat (1-12)
        jahr: Jahr
        aktuelles_datum: Das aktuelle Datum
    
    Returns:
        Dict mit tagessatz, noch_benoetigt, ist_leads, soll_leads, arbeitstage_noch
    """
    status_info = berechne_makler_status(db, makler, monat, jahr)
    
    # Prüfe ob Makler neue Leads bekommen kann (für Lead-Zuweisungen)
    # WICHTIG: Verwendet kann_makler_neue_leads_bekommen statt ist_makler_in_monat_aktiv,
    # da pausierte Makler keine neuen Leads bekommen sollen
    if not kann_makler_neue_leads_bekommen(makler, monat, jahr):
        return {
            "tagessatz": 0,
            "noch_benoetigt": 0,
            "ist_leads": 0,
            "soll_leads": None,
            "arbeitstage_noch": 0,
            "kann_leads": False
        }
    
    ist_leads = status_info.get("ist_leads", 0)
    arbeitstage_noch = berechne_arbeitstage_bis_monatsende(aktuelles_datum)
    
    # Altes System
    if makler.rechnungssystem_typ == "alt" or (makler.rechnungssystem_typ is None):
        vertragsmonat = berechne_vertragsmonat(makler.vertragsstart_datum, monat, jahr)
        
        # Soll-Leads bestimmen
        if makler.monatliche_soll_leads is not None:
            soll_leads = makler.monatliche_soll_leads
        elif vertragsmonat == 1 and makler.testphase_leads > 0:
            soll_leads = makler.testphase_leads
        else:
            soll_leads = None  # Unbegrenzt
        
        if soll_leads is None:
            # Unbegrenzt: Kein Tagessatz, aber kann Leads bekommen
            return {
                "tagessatz": 0,  # Kein fester Tagessatz bei unbegrenzt
                "noch_benoetigt": None,  # Unbegrenzt
                "ist_leads": ist_leads,
                "soll_leads": None,
                "arbeitstage_noch": arbeitstage_noch,
                "kann_leads": True,
                "prioritaet": "normal"
            }
        else:
            noch_benoetigt = max(0, soll_leads - ist_leads)
            if noch_benoetigt == 0:
                tagessatz = 0
                prioritaet = "niedrig"
            elif arbeitstage_noch > 0:
                tagessatz = noch_benoetigt / arbeitstage_noch
                prioritaet = "hoch" if tagessatz >= 1.0 else "normal"
            else:
                tagessatz = noch_benoetigt  # Heute noch alles
                prioritaet = "hoch"
            
            return {
                "tagessatz": tagessatz,
                "noch_benoetigt": noch_benoetigt,
                "ist_leads": ist_leads,
                "soll_leads": soll_leads,
                "arbeitstage_noch": arbeitstage_noch,
                "kann_leads": noch_benoetigt > 0,
                "prioritaet": prioritaet
            }
    
    # Neues System (Credits)
    else:
        credits_stand = status_info.get("credits_stand", 0)
        verfuegbare_leads = status_info.get("verfuegbare_leads", 0)
        naechster_lead_preis = status_info.get("naechster_lead_preis", 0)
        
        if credits_stand < naechster_lead_preis:
            # Keine Credits
            return {
                "tagessatz": 0,
                "noch_benoetigt": 0,
                "ist_leads": ist_leads,
                "soll_leads": None,
                "arbeitstage_noch": arbeitstage_noch,
                "kann_leads": False,
                "prioritaet": "niedrig"
            }
        
        # Bei Credits-System: Verfuegbare Leads gleichmäßig verteilen
        if verfuegbare_leads == 0:
            tagessatz = 0
            prioritaet = "niedrig"
        elif arbeitstage_noch > 0:
            # Gleichmäßige Verteilung der verfügbaren Leads
            tagessatz = verfuegbare_leads / arbeitstage_noch
            prioritaet = "hoch" if tagessatz >= 1.0 else "normal"
        else:
            tagessatz = verfuegbare_leads
            prioritaet = "hoch"
        
        return {
            "tagessatz": tagessatz,
            "noch_benoetigt": verfuegbare_leads,
            "ist_leads": ist_leads,
            "soll_leads": None,  # Credits-System hat kein festes Soll
            "arbeitstage_noch": arbeitstage_noch,
            "kann_leads": verfuegbare_leads > 0,
            "prioritaet": prioritaet,
            "credits_stand": credits_stand,
            "verfuegbare_leads": verfuegbare_leads
        }


def zaehle_leads_heute_fuer_makler(
    db: Session,
    makler_id: int,
    aktuelles_datum: date
) -> int:
    """
    Zählt, wie viele Leads ein Makler heute bereits qualifiziert bekommen hat.
    
    Args:
        db: Datenbank-Session
        makler_id: ID des Maklers
        aktuelles_datum: Das aktuelle Datum
    
    Returns:
        Anzahl der heute qualifizierten Leads für diesen Makler
    """
    heute_start = datetime.combine(aktuelles_datum, datetime.min.time())
    heute_ende = datetime.combine(aktuelles_datum, datetime.max.time())
    
    anzahl = (
        db.query(Lead)
        .filter(
            and_(
                Lead.makler_id == makler_id,
                Lead.status.in_(["qualifiziert", "geliefert"]),
                Lead.qualifiziert_am >= heute_start,
                Lead.qualifiziert_am <= heute_ende
            )
        )
        .count()
    )
    
    return anzahl


def finde_besten_lead_fuer_telefonist(
    db: Session,
    unqualifizierte_leads: List[Lead],
    alle_makler: List[Makler],
    aktueller_user_id: Optional[int] = None
) -> Optional[Dict[str, Any]]:
    """
    Findet den besten Lead, den ein Telefonist als nächstes anrufen soll,
    und schlägt direkt einen Makler für die Qualifizierung vor.
    
    Algorithmus für gleichmäßige Verteilung:
    1. Berechne für jeden Makler den Tagessatz (noch_benoetigt / arbeitstage_noch)
    2. Zähle, wie viele Leads jeder Makler heute bereits bekommen hat
    3. Berechne den "Rückstand" = tagessatz - leads_heute
    4. Priorisiere Makler mit höchstem Rückstand (braucht noch am meisten heute)
    5. Finde Leads, die zu diesem Makler passen (PLZ/Gebiet)
    6. Nimm den ältesten passenden Lead
    
    WICHTIG: Der Algorithmus sorgt für gleichmäßige Verteilung über den Monat.
    
    Args:
        db: Datenbank-Session
        unqualifizierte_leads: Liste aller unqualifizierten Leads
        alle_makler: Liste aller Makler
    
    Returns:
        Dict mit lead_id, makler_id, makler_name, grund, tagessatz oder None
    """
    if not unqualifizierte_leads:
        return None
    
    jetzt = datetime.now()
    aktuelles_datum = jetzt.date()
    aktueller_monat = jetzt.month
    aktuelles_jahr = jetzt.year
    
    # Berechne Tagessatz und Rückstand für alle aktiven Makler
    makler_tagessaetze = []
    
    for makler in alle_makler:
        tagessatz_info = berechne_tagessatz_fuer_makler(
            db, makler, aktueller_monat, aktuelles_jahr, aktuelles_datum
        )
        
        if tagessatz_info["kann_leads"]:
            # Zähle Leads, die der Makler heute bereits bekommen hat
            leads_heute = zaehle_leads_heute_fuer_makler(db, makler.id, aktuelles_datum)
            
            # Berechne Rückstand: Wie viele Leads fehlen noch heute?
            tagessatz = tagessatz_info["tagessatz"]
            if tagessatz is None or tagessatz == 0:
                # Unbegrenzt oder kein Tagessatz: Rückstand = 1 (immer priorisieren)
                rueckstand = 1.0
            else:
                rueckstand = max(0, tagessatz - leads_heute)
            
            makler_tagessaetze.append({
                "makler": makler,
                "tagessatz": tagessatz_info["tagessatz"],
                "noch_benoetigt": tagessatz_info["noch_benoetigt"],
                "prioritaet": tagessatz_info["prioritaet"],
                "leads_heute": leads_heute,
                "rueckstand": rueckstand,
                **tagessatz_info
            })
    
    # Sortiere nach Rückstand (höchster zuerst) für gleichmäßige Verteilung
    # Makler mit höherem Rückstand werden zuerst bedient
    makler_tagessaetze.sort(key=lambda x: (
        0 if x["prioritaet"] == "hoch" else 1 if x["prioritaet"] == "normal" else 2,
        -x["rueckstand"]  # Höchster Rückstand zuerst = gleichmäßigste Verteilung
    ))
    
    # Für jeden Makler (beginnend mit höchstem Tagessatz) suche passende Leads
    for makler_info in makler_tagessaetze:
        makler = makler_info["makler"]
        
        # Parse Gebiet des Maklers
        makler_plz_liste = []
        if makler.gebiet:
            makler_plz_liste = [plz.strip() for plz in makler.gebiet.split(",") if plz.strip()]
        
        # Finde Leads, die zu diesem Makler passen
        passende_leads = []
        
        for lead in unqualifizierte_leads:
            # Prüfe ob Lead bereits einem Makler zugeordnet ist
            if lead.makler_id:
                continue
            
            # Prüfe PLZ-Match
            if lead.postleitzahl:
                lead_plz = lead.postleitzahl.strip()
                if makler_plz_liste and lead_plz in makler_plz_liste:
                    passende_leads.append(lead)
                elif not makler_plz_liste:
                    # Makler hat kein Gebiet definiert - kann alle Leads bekommen
                    passende_leads.append(lead)
            elif not makler_plz_liste:
                # Lead hat keine PLZ, Makler hat kein Gebiet - passt
                passende_leads.append(lead)
        
        # Wenn passende Leads gefunden, nimm den ältesten
        if passende_leads:
            # Sortiere nach Erstellungsdatum (ältester zuerst)
            passende_leads.sort(key=lambda l: l.erstellt_am if l.erstellt_am else datetime.min)
            bester_lead = passende_leads[0]
            
            # Formuliere klaren Grund mit Info zur gleichmäßigen Verteilung
            if makler_info["tagessatz"] and makler_info["tagessatz"] > 0:
                leads_heute = makler_info.get("leads_heute", 0)
                grund = f"Qualifiziere für {makler.firmenname} - benötigt {makler_info['tagessatz']:.1f} Leads/Tag (heute: {leads_heute}/{makler_info['tagessatz']:.1f}, noch {makler_info['noch_benoetigt']} im Monat)"
            elif makler_info["noch_benoetigt"] is None:
                grund = f"Qualifiziere für {makler.firmenname} - unbegrenzte Leads möglich"
            else:
                grund = f"Qualifiziere für {makler.firmenname} - noch {makler_info['noch_benoetigt']} Leads im Monat"
            
            return {
                "lead_id": bester_lead.id,
                "lead_nummer": bester_lead.lead_nummer or bester_lead.id,
                "makler_id": makler.id,
                "makler_name": makler.firmenname,
                "grund": grund,
                "tagessatz": makler_info["tagessatz"],
                "noch_benoetigt": makler_info["noch_benoetigt"],
                "prioritaet": makler_info["prioritaet"],
                "postleitzahl": bester_lead.postleitzahl,
                "ort": bester_lead.ort,
                "empfehlung": f"Qualifiziere Lead #{bester_lead.lead_nummer or bester_lead.id} für {makler.firmenname}"
            }
    
    # Falls kein Makler mit passenden Leads gefunden wurde, aber es gibt Makler die Leads brauchen,
    # nimm den ersten verfügbaren Makler und den ältesten Lead
    if makler_tagessaetze and unqualifizierte_leads:
        # Nimm den Makler mit höchster Priorität
        bester_makler_info = makler_tagessaetze[0]
        bester_makler = bester_makler_info["makler"]
        
        # Nimm den ältesten unqualifizierten Lead (ohne Makler-Zuordnung)
        unqualifizierte_ohne_makler = [l for l in unqualifizierte_leads if not l.makler_id]
        if unqualifizierte_ohne_makler:
            unqualifizierte_ohne_makler.sort(key=lambda l: l.erstellt_am if l.erstellt_am else datetime.min)
            bester_lead = unqualifizierte_ohne_makler[0]
            
            grund = f"Qualifiziere für {bester_makler.firmenname} - passt zu Gebiet"
            if bester_makler_info["tagessatz"] > 0:
                grund += f" (benötigt {bester_makler_info['tagessatz']:.1f} Leads/Tag)"
            
            return {
                "lead_id": bester_lead.id,
                "lead_nummer": bester_lead.lead_nummer or bester_lead.id,
                "makler_id": bester_makler.id,
                "makler_name": bester_makler.firmenname,
                "grund": grund,
                "tagessatz": bester_makler_info["tagessatz"],
                "noch_benoetigt": bester_makler_info["noch_benoetigt"],
                "prioritaet": bester_makler_info["prioritaet"],
                "postleitzahl": bester_lead.postleitzahl,
                "ort": bester_lead.ort,
                "empfehlung": f"Qualifiziere Lead #{bester_lead.lead_nummer or bester_lead.id} für {bester_makler.firmenname}"
            }
    
    # Fallback: Nur Lead ohne Makler-Vorschlag (sollte selten vorkommen)
    if unqualifizierte_leads:
        unqualifizierte_ohne_makler = [l for l in unqualifizierte_leads if not l.makler_id]
        if unqualifizierte_ohne_makler:
            unqualifizierte_ohne_makler.sort(key=lambda l: l.erstellt_am if l.erstellt_am else datetime.min)
            aeltester_lead = unqualifizierte_ohne_makler[0]
            
            return {
                "lead_id": aeltester_lead.id,
                "lead_nummer": aeltester_lead.lead_nummer or aeltester_lead.id,
                "makler_id": None,
                "makler_name": None,
                "grund": "Kein Makler verfügbar - bitte manuell zuordnen",
                "tagessatz": 0,
                "noch_benoetigt": 0,
                "prioritaet": "niedrig",
                "postleitzahl": aeltester_lead.postleitzahl,
                "ort": aeltester_lead.ort,
                "empfehlung": f"Lead #{aeltester_lead.lead_nummer or aeltester_lead.id} anrufen - Makler manuell zuordnen"
            }
    
    return None


def ist_lead_gesperrt(
    lead: Lead,
    aktueller_user_id: Optional[int] = None,
    timeout_minuten: int = 30
) -> bool:
    """
    Prüft, ob ein Lead gesperrt ist (von einem anderen Telefonisten bearbeitet wird).
    
    Args:
        lead: Der Lead
        aktueller_user_id: ID des aktuellen Benutzers (wenn None, wird Lead als gesperrt betrachtet wenn bearbeitet_von_user_id gesetzt ist)
        timeout_minuten: Nach wie vielen Minuten ein Lock automatisch abläuft
    
    Returns:
        True wenn Lead gesperrt ist, False wenn verfügbar
    """
    if not lead.bearbeitet_von_user_id:
        return False  # Lead ist nicht gesperrt
    
    # Wenn aktueller Benutzer der Bearbeiter ist, ist der Lead nicht gesperrt
    if aktueller_user_id and lead.bearbeitet_von_user_id == aktueller_user_id:
        return False
    
    # Prüfe Timeout: Wenn Lock älter als timeout_minuten ist, gilt er als abgelaufen
    if lead.bearbeitet_seit:
        lock_alter = (datetime.now() - lead.bearbeitet_seit).total_seconds() / 60
        if lock_alter > timeout_minuten:
            return False  # Lock ist abgelaufen
    
    return True  # Lead ist gesperrt


def get_lead_empfehlung_fuer_telefonist(
    db: Session,
    aktueller_user_id: Optional[int] = None
) -> Dict[str, Any]:
    """
    Hauptfunktion: Gibt eine Lead-Empfehlung für den Telefonisten zurück.
    
    Args:
        db: Datenbank-Session
        aktueller_user_id: ID des aktuellen Telefonisten (für Locking)
    
    Returns:
        Dict mit empfehlung (Lead-Empfehlung) und uebersicht (alle Makler mit Tagessätzen)
    """
    jetzt = datetime.now()
    aktuelles_datum = jetzt.date()
    aktueller_monat = jetzt.month
    aktuelles_jahr = jetzt.year
    
    # Hole alle unqualifizierten Leads, die nicht von anderen Telefonisten bearbeitet werden
    unqualifizierte_leads_query = (
        db.query(Lead)
        .filter(Lead.status == "unqualifiziert")
    )
    
    # Filtere Leads, die von anderen Telefonisten bearbeitet werden (außer wenn Lock abgelaufen ist)
    unqualifizierte_leads = []
    for lead in unqualifizierte_leads_query.all():
        if not ist_lead_gesperrt(lead, aktueller_user_id):
            unqualifizierte_leads.append(lead)
    
    # Hole alle aktiven Makler
    alle_makler = db.query(Makler).all()
    
    # Finde besten Lead (mit Locking-Berücksichtigung)
    empfehlung = finde_besten_lead_fuer_telefonist(db, unqualifizierte_leads, alle_makler, aktueller_user_id)
    
    # Berechne Übersicht für alle Makler (nur aktive, nicht pausierte)
    uebersicht = []
    for makler in alle_makler:
        # Prüfe ob Makler pausiert ist - pausierte Makler werden nicht in der Übersicht angezeigt
        if not kann_makler_neue_leads_bekommen(makler, aktueller_monat, aktuelles_jahr):
            continue  # Überspringe pausierte Makler
        
        tagessatz_info = berechne_tagessatz_fuer_makler(
            db, makler, aktueller_monat, aktuelles_jahr, aktuelles_datum
        )
        
        if tagessatz_info["kann_leads"]:
            uebersicht.append({
                "makler_id": makler.id,
                "makler_name": makler.firmenname,
                "tagessatz": tagessatz_info["tagessatz"],
                "noch_benoetigt": tagessatz_info["noch_benoetigt"],
                "ist_leads": tagessatz_info["ist_leads"],
                "soll_leads": tagessatz_info["soll_leads"],
                "prioritaet": tagessatz_info["prioritaet"],
                "arbeitstage_noch": tagessatz_info["arbeitstage_noch"]
            })
    
    # Sortiere Übersicht nach Priorität und Tagessatz
    uebersicht.sort(key=lambda x: (
        0 if x["prioritaet"] == "hoch" else 1 if x["prioritaet"] == "normal" else 2,
        -x["tagessatz"]
    ))
    
    # Berechne minimalen Tagessatz: Summe aller noch benötigten Leads / verbleibende Arbeitstage
    arbeitstage_noch = berechne_arbeitstage_bis_monatsende(aktuelles_datum)
    
    # Summiere alle noch benötigten Leads (nur Makler mit festen Soll-Leads, nicht unbegrenzt)
    gesamt_noch_benoetigt = 0
    for m in uebersicht:
        noch_benoetigt = m.get("noch_benoetigt")
        # Nur zählen wenn noch_benoetigt eine Zahl ist (nicht None = unbegrenzt)
        if noch_benoetigt is not None and noch_benoetigt > 0:
            gesamt_noch_benoetigt += noch_benoetigt
    
    # Berechne minimalen Tagessatz: Gesamt noch benötigt / verbleibende Arbeitstage
    if arbeitstage_noch > 0:
        minimaler_tagessatz = gesamt_noch_benoetigt / arbeitstage_noch
    else:
        # Wenn keine Arbeitstage mehr übrig sind, ist der Tagessatz = noch benötigt
        minimaler_tagessatz = gesamt_noch_benoetigt
    
    return {
        "empfehlung": empfehlung,
        "uebersicht": uebersicht,
        "aktuelles_datum": aktuelles_datum.isoformat(),
        "arbeitstage_noch": arbeitstage_noch,
        "minimaler_tagessatz": minimaler_tagessatz,
        "gesamt_noch_benoetigt": gesamt_noch_benoetigt
    }

