from datetime import date, datetime, timedelta
from typing import Tuple, Optional, List, Dict, Any
from sqlalchemy import func, extract
from sqlalchemy.orm import Session

from ..models import Makler, Lead, MaklerCredits


def berechne_credits_stand(db: Session, makler_id: int) -> float:
    """
    Berechnet den aktuellen Credits-Stand eines Maklers.
    """
    result = db.query(func.sum(MaklerCredits.betrag)).filter(
        MaklerCredits.makler_id == makler_id
    ).scalar()
    
    return float(result) if result is not None else 0.0


def berechne_preis_fuer_lead(
    makler: Makler,
    lead_qualifiziert_am: datetime,
    anzahl_leads_im_monat: int
) -> float:
    """
    Berechnet den Preis für einen Lead basierend auf der neuen Preislogik:
    - Erste X Leads im ersten Monat: erste_leads_preis (Standard: 50€)
    - Alles über X Leads im ersten Monat: erste_leads_danach_preis (Standard: 75€)
    - Ab 2. Monat: standard_preis (Standard: 100€)
    
    Args:
        makler: Der Makler
        lead_qualifiziert_am: Datum/Zeit wann der Lead qualifiziert wurde
        anzahl_leads_im_monat: Anzahl der bereits qualifizierten Leads in diesem Monat (inkl. diesem Lead)
    
    Returns:
        Preis für diesen Lead in Euro
    """
    # Bestimme Vertragsmonat
    vertragsstart = makler.vertragsstart_datum
    qualifiziert_datum = lead_qualifiziert_am.date() if isinstance(lead_qualifiziert_am, datetime) else lead_qualifiziert_am
    
    # Berechne Vertragsmonat (1-basiert)
    diff_monate = (qualifiziert_datum.year - vertragsstart.year) * 12 + (qualifiziert_datum.month - vertragsstart.month)
    vertragsmonat = diff_monate + 1
    
    # Hole Preis-Konfiguration (mit Defaults)
    erste_leads_anzahl = makler.erste_leads_anzahl if makler.erste_leads_anzahl is not None else 5
    erste_leads_preis = makler.erste_leads_preis if makler.erste_leads_preis is not None else 50.0
    erste_leads_danach_preis = makler.erste_leads_danach_preis if makler.erste_leads_danach_preis is not None else 75.0
    standard_preis = makler.standard_preis if makler.standard_preis is not None else 100.0
    
    # Wenn Makler pausiert war und wieder anfängt: Startet mit Standard-Preis
    # (Prüfe ob es der erste Monat nach einer Pause ist - vereinfacht: wenn vertragsmonat > 1, Standard-Preis)
    # TODO: Bessere Logik für Pause-Erkennung falls nötig
    
    # Preislogik
    if vertragsmonat == 1:
        # Erster Monat: Erste X Leads = erste_leads_preis, danach = erste_leads_danach_preis
        if anzahl_leads_im_monat <= erste_leads_anzahl:
            return erste_leads_preis
        else:
            return erste_leads_danach_preis
    else:
        # Ab 2. Monat: Standard-Preis
        return standard_preis


def zaehle_leads_im_monat(
    db: Session,
    makler_id: int,
    monat: int,
    jahr: int
) -> int:
    """
    Zählt alle qualifizierten Leads eines Maklers in einem bestimmten Monat.
    """
    return (
        db.query(Lead)
        .filter(
            Lead.makler_id == makler_id,
            Lead.status == "qualifiziert",
            Lead.qualifiziert_am.isnot(None),
            extract("month", Lead.qualifiziert_am) == monat,
            extract("year", Lead.qualifiziert_am) == jahr,
        )
        .count()
    )


def pruefe_und_buche_credits_fuer_lead(
    db: Session,
    makler: Makler,
    lead_id: int,
    lead_qualifiziert_am: datetime
) -> Tuple[bool, Optional[str], Optional[float]]:
    """
    Prüft ob genug Credits vorhanden sind und bucht sie ab.
    
    Args:
        db: Datenbank-Session
        makler: Der Makler
        lead_id: ID des Leads
        lead_qualifiziert_am: Datum/Zeit wann der Lead qualifiziert wurde
    
    Returns:
        Tuple (erfolg: bool, fehlermeldung: Optional[str], preis: Optional[float])
    """
    # Nur für Credits-System
    if makler.rechnungssystem_typ != "neu":
        return True, None, None  # Altes System: Keine Credits-Prüfung
    
    # Berechne Preis für diesen Lead
    qualifiziert_datum = lead_qualifiziert_am.date() if isinstance(lead_qualifiziert_am, datetime) else lead_qualifiziert_am
    # Zähle Leads im Monat (ohne den aktuellen Lead, da er noch nicht committed ist)
    anzahl_leads_im_monat = zaehle_leads_im_monat(
        db, makler.id, qualifiziert_datum.month, qualifiziert_datum.year
    )
    # Füge 1 hinzu für den aktuellen Lead
    anzahl_leads_im_monat += 1
    
    preis = berechne_preis_fuer_lead(makler, lead_qualifiziert_am, anzahl_leads_im_monat)
    
    # Prüfe Credits-Stand
    aktueller_stand = berechne_credits_stand(db, makler.id)
    
    if aktueller_stand < preis:
        return False, f"Nicht genug Credits. Benötigt: {preis:.2f}€, Vorhanden: {aktueller_stand:.2f}€", preis
    
    # Buche Credits ab
    transaktion = MaklerCredits(
        makler_id=makler.id,
        betrag=-preis,  # Negativer Betrag = Abbuchung
        transaktionstyp="lead_abbuchung",
        lead_id=lead_id,
        beschreibung=f"Lead #{lead_id} - {preis:.2f}€"
    )
    
    db.add(transaktion)
    db.commit()
    
    return True, None, preis


def erstelle_erstattung_fuer_lead(
    db: Session,
    makler: Makler,
    lead_id: int,
    beschreibung: Optional[str] = None
) -> Optional[MaklerCredits]:
    """
    Erstellt eine Erstattung für einen Lead (z.B. bei Reklamation oder Stornierung).
    Gibt die Transaktion zurück oder None falls keine Erstattung möglich ist.
    """
    # Nur für Credits-System
    if makler.rechnungssystem_typ != "neu":
        return None
    
    # Finde die ursprüngliche Abbuchung
    ursprüngliche_abbuchung = (
        db.query(MaklerCredits)
        .filter(
            MaklerCredits.makler_id == makler.id,
            MaklerCredits.lead_id == lead_id,
            MaklerCredits.transaktionstyp == "lead_abbuchung"
        )
        .first()
    )
    
    if not ursprüngliche_abbuchung:
        return None  # Keine ursprüngliche Abbuchung gefunden
    
    # Erstelle Erstattung (positiver Betrag = Aufladung)
    erstattung = MaklerCredits(
        makler_id=makler.id,
        betrag=abs(ursprüngliche_abbuchung.betrag),  # Positiver Betrag
        transaktionstyp="erstattung",
        lead_id=lead_id,
        beschreibung=beschreibung or f"Erstattung für Lead #{lead_id}"
    )
    
    db.add(erstattung)
    db.commit()
    db.refresh(erstattung)
    
    return erstattung


def berechne_rueckzahlbare_credits(
    db: Session,
    makler_id: int,
    monate: int = 2
) -> List[Dict[str, Any]]:
    """
    Berechnet, welche Credits zurückgezahlt werden können.
    Credits können zurückgezahlt werden, wenn:
    - Sie älter als X Monate sind (Standard: 2 Monate)
    - Sie noch nicht vollständig für Leads verwendet wurden (FIFO-Prinzip)
    
    Args:
        db: Datenbank-Session
        makler_id: ID des Maklers
        monate: Anzahl Monate, nach denen Credits zurückgezahlt werden können (Standard: 2)
    
    Returns:
        Liste von Dicts mit Informationen über rückzahlbare Credits
    """
    heute = datetime.utcnow()
    grenzdatum = heute - timedelta(days=monate * 30)  # Vereinfacht: 30 Tage pro Monat
    
    # Hole alle Aufladungen (positive Beträge), sortiert nach Datum (älteste zuerst)
    aufladungen = (
        db.query(MaklerCredits)
        .filter(
            MaklerCredits.makler_id == makler_id,
            MaklerCredits.betrag > 0,
            MaklerCredits.transaktionstyp.in_(["aufladung", "zahlung_online", "manuelle_anpassung"]),
            MaklerCredits.erstellt_am <= grenzdatum
        )
        .order_by(MaklerCredits.erstellt_am.asc())
        .all()
    )
    
    # Hole alle Abbuchungen (negative Beträge), sortiert nach Datum
    abbuchungen = (
        db.query(MaklerCredits)
        .filter(
            MaklerCredits.makler_id == makler_id,
            MaklerCredits.betrag < 0
        )
        .order_by(MaklerCredits.erstellt_am.asc())
        .all()
    )
    
    # Prüfe ob bereits Rückzahlungen existieren
    rueckzahlungen = (
        db.query(MaklerCredits)
        .filter(
            MaklerCredits.makler_id == makler_id,
            MaklerCredits.transaktionstyp == "rueckzahlung"
        )
        .all()
    )
    
    # FIFO-Simulation: Welche Aufladungen wurden bereits "verwendet"?
    rueckzahlbare = []
    verbleibende_abbuchungen = sum(abs(a.betrag) for a in abbuchungen)
    
    # Ziehe bereits zurückgezahlte Beträge ab
    for rueckzahlung in rueckzahlungen:
        if rueckzahlung.zahlungsreferenz:
            try:
                transaktion_id = int(rueckzahlung.zahlungsreferenz)
                # Finde ursprüngliche Transaktion
                ursprüngliche = next((a for a in aufladungen if a.id == transaktion_id), None)
                if ursprüngliche:
                    # Diese Aufladung wurde bereits zurückgezahlt
                    verbleibende_abbuchungen += abs(rueckzahlung.betrag)  # Rückzahlung "gibt" Credits zurück
            except ValueError:
                pass
    
    for aufladung in aufladungen:
        # Prüfe ob bereits eine Rückzahlung für diese Transaktion existiert
        bereits_zurueckgezahlt = any(
            r.zahlungsreferenz == str(aufladung.id) 
            for r in rueckzahlungen
        )
        if bereits_zurueckgezahlt:
            continue
        
        aufladungsbetrag = aufladung.betrag
        
        # Prüfe ob diese Aufladung bereits vollständig verwendet wurde
        if verbleibende_abbuchungen >= aufladungsbetrag:
            # Diese Aufladung wurde vollständig verwendet
            verbleibende_abbuchungen -= aufladungsbetrag
            continue
        
        # Berechne noch nicht verwendeten Betrag
        verwendeter_betrag = verbleibende_abbuchungen
        verbleibende_abbuchungen = 0  # Alle weiteren Abbuchungen sind aufgebraucht
        
        rueckzahlbarer_betrag = aufladungsbetrag - verwendeter_betrag
        
        if rueckzahlbarer_betrag > 0:
            rueckzahlbare.append({
                "transaktion_id": aufladung.id,
                "betrag": rueckzahlbarer_betrag,
                "ursprünglicher_betrag": aufladungsbetrag,
                "erstellt_am": aufladung.erstellt_am.isoformat(),
                "beschreibung": aufladung.beschreibung or f"Aufladung vom {aufladung.erstellt_am.strftime('%d.%m.%Y')}",
                "transaktionstyp": aufladung.transaktionstyp,
                "tage_alt": (heute - aufladung.erstellt_am).days
            })
    
    return rueckzahlbare


def erstelle_rueckzahlung(
    db: Session,
    makler: Makler,
    transaktion_id: int,
    betrag: float,
    beschreibung: Optional[str] = None
) -> MaklerCredits:
    """
    Erstellt eine Rückzahlung für nicht verwendete Credits.
    
    Args:
        db: Datenbank-Session
        makler: Der Makler
        transaktion_id: ID der ursprünglichen Aufladungs-Transaktion
        betrag: Betrag der zurückgezahlt werden soll
        beschreibung: Optionale Beschreibung
    
    Returns:
        Erstellte Rückzahlungs-Transaktion
    """
    # Prüfe ob Makler Credits-System verwendet
    if makler.rechnungssystem_typ != "neu":
        raise ValueError("Makler verwendet nicht das Credits-System")
    
    # Prüfe ob Transaktion existiert und zum Makler gehört
    ursprüngliche_transaktion = (
        db.query(MaklerCredits)
        .filter(
            MaklerCredits.id == transaktion_id,
            MaklerCredits.makler_id == makler.id,
            MaklerCredits.betrag > 0
        )
        .first()
    )
    
    if not ursprüngliche_transaktion:
        raise ValueError("Ursprüngliche Transaktion nicht gefunden")
    
    # Prüfe ob bereits eine Rückzahlung für diese Transaktion existiert
    bestehende_rueckzahlung = (
        db.query(MaklerCredits)
        .filter(
            MaklerCredits.makler_id == makler.id,
            MaklerCredits.transaktionstyp == "rueckzahlung",
            MaklerCredits.zahlungsreferenz == str(transaktion_id)
        )
        .first()
    )
    
    if bestehende_rueckzahlung:
        raise ValueError("Für diese Transaktion existiert bereits eine Rückzahlung")
    
    # Prüfe ob genug Credits vorhanden sind
    aktueller_stand = berechne_credits_stand(db, makler.id)
    if aktueller_stand < betrag:
        raise ValueError(f"Nicht genug Credits vorhanden. Verfügbar: {aktueller_stand:.2f}€, Angefragt: {betrag:.2f}€")
    
    # Erstelle Rückzahlung (negativer Betrag = Abbuchung)
    rueckzahlung = MaklerCredits(
        makler_id=makler.id,
        betrag=-betrag,  # Negativer Betrag = Abbuchung
        transaktionstyp="rueckzahlung",
        beschreibung=beschreibung or f"Rückzahlung für nicht verwendete Credits (Transaktion #{transaktion_id})",
        zahlungsreferenz=str(transaktion_id)  # Verweise auf ursprüngliche Transaktion
    )
    
    db.add(rueckzahlung)
    db.commit()
    db.refresh(rueckzahlung)
    
    return rueckzahlung

