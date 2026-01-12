from datetime import date
from typing import Tuple
from calendar import monthrange

from sqlalchemy.orm import Session

from ..models import Lead, Makler, Rechnung


def berechne_vertragsmonat(vertragsstart: date, abrechnungsmonat: int, jahr: int) -> int:
    """
    Berechnet den Vertragsmonat (1-basiert) relativ zum Vertragsstart.
    Beispiel:
      - Vertragsstart 2025-01-15, Abrechnung 2025-01 -> Vertragsmonat 1
      - Vertragsstart 2025-01-15, Abrechnung 2025-02 -> Vertragsmonat 2
    """
    start_monat = vertragsstart.month
    start_jahr = vertragsstart.year

    diff = (jahr - start_jahr) * 12 + (abrechnungsmonat - start_monat)
    return diff + 1  # 1-basiert


def bestimme_preis_pro_lead(makler: Makler, vertragsmonat: int, anzahl_leads_im_monat: int = 0) -> float:
    """
    Berechnet den Preis für einen Lead (altes System, monatliche Rechnungen).
    
    Preislogik:
      - Vertragsmonat 1, erste testphase_leads Leads: testphase_preis
      - Vertragsmonat 1, Leads über testphase_leads: standard_preis
      - Ab Vertragsmonat 2: standard_preis
    
    Args:
        makler: Der Makler
        vertragsmonat: Vertragsmonat (1-basiert)
        anzahl_leads_im_monat: Anzahl der Leads in diesem Monat (0 = erwarteter Preis für nächsten Lead)
    
    Returns:
        Preis pro Lead in Euro
    """
    standard_preis = makler.standard_preis if makler.standard_preis is not None else 0.0
    
    if vertragsmonat == 1:
        # Im ersten Monat: Erste testphase_leads Leads zum Testphase-Preis
        testphase_leads = makler.testphase_leads if makler.testphase_leads is not None else 0
        if testphase_leads > 0:
            # Wenn anzahl_leads_im_monat = 0, nehmen wir an, dass es der erste Lead ist
            if anzahl_leads_im_monat == 0 or anzahl_leads_im_monat <= testphase_leads:
                testphase_preis = makler.testphase_preis if makler.testphase_preis is not None else standard_preis
                return testphase_preis
        # Leads über testphase_leads zum Standard-Preis (oder wenn keine Testphase)
        return standard_preis
    
    # Ab 2. Monat: Standard-Preis
    return standard_preis


def ist_makler_in_monat_aktiv(makler: Makler, monat: int, jahr: int, db: Session = None) -> bool:
    """
    Prüft, ob der Makler im angegebenen Monat/Jahr aktiv ist (nicht pausiert und nicht gekündigt).
    
    WICHTIG für Abrechnungen: Wenn bereits Leads im Monat geliefert wurden, werden diese trotzdem 
    abgerechnet, auch wenn der Vertrag später pausiert wurde.
    
    Rückgabewert:
      - True, wenn bereits Leads im Monat geliefert wurden (auch wenn pausiert) ODER
      - True, wenn Makler aktiv ist (nicht pausiert und nicht gekündigt)
      - False, sonst
    """
    from datetime import datetime
    
    # Prüfe zuerst, ob bereits Leads im Monat geliefert wurden
    # Wenn ja, dann ist der Makler für Abrechnungszwecke aktiv
    if db is not None:
        try:
            anzahl_leads = ermittle_anzahl_gelieferter_leads(db, makler.id, monat, jahr)
            if anzahl_leads > 0:
                return True  # Bereits gelieferte Leads werden immer abgerechnet
        except Exception:
            # Bei Fehler bei der Datenbankabfrage, ignoriere diese Prüfung
            pass
    
    # Prüfe auf Vertragspause: Wenn vertrag_pausiert == 1, dann ist der Vertrag für den aktuellen Monat pausiert
    if makler.vertrag_pausiert == 1:
        # Berechne den aktuellen Monat (vom heutigen Datum aus)
        jetzt = datetime.now()
        aktueller_monat = jetzt.month
        aktuelles_jahr = jetzt.year
        
        # Prüfe, ob der Abrechnungsmonat >= aktueller Monat ist
        abrechnungs_datum = date(jahr, monat, 1)
        aktueller_monat_datum = date(aktuelles_jahr, aktueller_monat, 1)
        
        if abrechnungs_datum >= aktueller_monat_datum:
            return False  # Vertrag ist für diesen Monat pausiert
    
    # Prüfe auf Kündigung: Wenn vertrag_bis gesetzt ist und im oder vor dem Monat liegt
    if makler.vertrag_bis is not None:
        # Berechne das erste und letzte Datum des Abrechnungsmonats
        monatsanfang = date(jahr, monat, 1)
        _, last_day = monthrange(jahr, monat)
        monatsende = date(jahr, monat, last_day)
        
        # Wenn das Kündigungsdatum vor oder am Monatsende liegt, ist der Vertrag für diesen Monat gekündigt
        # Beispiel: vertrag_bis = 2025-12-01, Monat = 12 -> 2025-12-01 <= 2025-12-31 -> gekündigt
        if makler.vertrag_bis <= monatsende:
            return False  # Vertrag ist für diesen Monat gekündigt
    
    return True  # Makler ist aktiv


def kann_makler_neue_leads_bekommen(makler: Makler, monat: int, jahr: int) -> bool:
    """
    Prüft, ob ein Makler neue Leads bekommen kann (für Lead-Zuweisungen).
    
    Diese Funktion ist strenger als ist_makler_in_monat_aktiv:
    - Wenn pausiert, werden KEINE neuen Leads zugewiesen (auch wenn bereits Leads geliefert wurden)
    - Wenn gekündigt, werden KEINE neuen Leads zugewiesen
    
    Rückgabewert:
      - False, wenn der Makler pausiert ist (vertrag_pausiert == 1 UND Monat >= aktueller Monat) ODER
      - False, wenn der Vertrag bereits gekündigt ist (vertrag_bis < Monatsende)
      - True, sonst
    """
    from datetime import datetime
    
    # Prüfe auf Vertragspause: Wenn vertrag_pausiert == 1, dann bekommt der Makler keine neuen Leads
    if makler.vertrag_pausiert == 1:
        # Berechne den aktuellen Monat (vom heutigen Datum aus)
        jetzt = datetime.now()
        aktueller_monat = jetzt.month
        aktuelles_jahr = jetzt.year
        
        # Prüfe, ob der Monat >= aktueller Monat ist
        monats_datum = date(jahr, monat, 1)
        aktueller_monat_datum = date(aktuelles_jahr, aktueller_monat, 1)
        
        if monats_datum >= aktueller_monat_datum:
            return False  # Vertrag ist pausiert - keine neuen Leads
    
    # Prüfe auf Kündigung: Wenn vertrag_bis gesetzt ist und im oder vor dem Monat liegt
    if makler.vertrag_bis is not None:
        # Berechne das erste und letzte Datum des Monats
        _, last_day = monthrange(jahr, monat)
        monatsende = date(jahr, monat, last_day)
        
        # Wenn das Kündigungsdatum vor oder am Monatsende liegt, bekommt der Makler keine neuen Leads
        if makler.vertrag_bis <= monatsende:
            return False  # Vertrag ist gekündigt - keine neuen Leads
    
    return True  # Makler kann neue Leads bekommen


def ermittle_anzahl_gelieferter_leads(
    db: Session, makler_id: int, monat: int, jahr: int
) -> int:
    """
    Zählt alle qualifizierten Leads des Maklers im angegebenen Monat.
    Ein Lead zählt nur, wenn er:
    - Status "qualifiziert" hat
    - Einem Makler zugeordnet ist
    - Im angegebenen Monat qualifiziert wurde (qualifiziert_am)
    """
    from sqlalchemy import extract, and_

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


def finde_oder_erzeuge_rechnung(
    db: Session,
    makler: Makler,
    monat: int,
    jahr: int,
) -> Tuple[Rechnung, bool]:
    """
    Findet eine vorhandene Rechnung für Makler/Monat/Jahr oder erstellt sie neu.
    Rückgabewert: (Rechnung, created_bool)
    """
    rechnung = (
        db.query(Rechnung)
        .filter(
            Rechnung.makler_id == makler.id,
            Rechnung.monat == monat,
            Rechnung.jahr == jahr,
        )
        .first()
    )

    # Zähle immer die gelieferten Leads (auch wenn pausiert - bereits gelieferte Leads werden abgerechnet)
    anzahl_leads = ermittle_anzahl_gelieferter_leads(db, makler.id, monat, jahr)
    
    # Prüfe, ob der Makler in diesem Monat aktiv ist (für Abrechnungszwecke)
    # WICHTIG: Wenn bereits Leads geliefert wurden, werden diese trotzdem abgerechnet
    ist_aktiv = ist_makler_in_monat_aktiv(makler, monat, jahr, db)
    
    # Aktuelle Werte immer neu berechnen (damit neue/stornierte Leads berücksichtigt werden)
    vertragsmonat = berechne_vertragsmonat(
        makler.vertragsstart_datum, monat, jahr
    )
    
    # Wenn der Makler in diesem Monat nicht aktiv ist (pausiert oder gekündigt) UND keine Leads geliefert wurden,
    # werden keine Leads berechnet
    if not ist_aktiv and anzahl_leads == 0:
        netto_betrag = 0.0
        preis_pro_lead = makler.standard_preis if makler.standard_preis is not None else 0.0
    else:
        
        # Berechne Gesamtpreis: Jeder Lead kann einen anderen Preis haben
        # (erste X Leads günstiger im ersten Monat)
        netto_betrag = 0.0
        testphase_leads = makler.testphase_leads if makler.testphase_leads is not None else 0
        testphase_preis = makler.testphase_preis if makler.testphase_preis is not None else makler.standard_preis
        standard_preis = makler.standard_preis if makler.standard_preis is not None else 0.0
        
        if vertragsmonat == 1 and testphase_leads > 0:
            # Erster Monat mit Testphase: Erste X Leads zum Testphase-Preis
            for i in range(1, anzahl_leads + 1):
                if i <= testphase_leads:
                    netto_betrag += testphase_preis
                else:
                    netto_betrag += standard_preis
            
            # Durchschnittspreis für Anzeige
            preis_pro_lead = netto_betrag / anzahl_leads if anzahl_leads > 0 else standard_preis
        else:
            # Ab 2. Monat oder keine Testphase: Alle Leads zum Standard-Preis
            netto_betrag = anzahl_leads * standard_preis
            preis_pro_lead = standard_preis
    
    # Berechnung: Netto = Gesamtpreis, dann 19% MwSt, dann Brutto = Netto + MwSt
    mwst_betrag = netto_betrag * 0.19
    gesamtbetrag = netto_betrag + mwst_betrag  # Brutto

    created = False
    if rechnung is None:
        # Neue Rechnung anlegen
        rechnung = Rechnung(
            makler_id=makler.id,
            monat=monat,
            jahr=jahr,
            anzahl_leads=anzahl_leads,
            preis_pro_lead=preis_pro_lead,
            gesamtbetrag=gesamtbetrag,
            status="offen",
        )
        db.add(rechnung)
        created = True
    else:
        # Bestehende Rechnung aktualisieren
        rechnung.anzahl_leads = anzahl_leads
        rechnung.preis_pro_lead = preis_pro_lead
        rechnung.gesamtbetrag = gesamtbetrag

    db.commit()
    db.refresh(rechnung)
    return rechnung, created


