from datetime import date

from sqlalchemy import Column, Date, Float, Integer, String, ForeignKey

from ..database import Base


class Makler(Base):
    """
    Repräsentiert einen Immobilienmakler, der Leads erhält und abgerechnet wird.
    """

    __tablename__ = "makler"

    id = Column(Integer, primary_key=True, index=True)
    firmenname = Column(String, nullable=False)
    ansprechpartner = Column(String, nullable=True)
    email = Column(String, nullable=False)
    adresse = Column(String, nullable=True)
    vertragsstart_datum = Column(Date, nullable=False)

    # Testphase: Anzahl der inkludierten Leads und Preis pro Lead in der Testphase
    testphase_leads = Column(Integer, nullable=False, default=0)
    testphase_preis = Column(Float, nullable=False, default=0.0)

    # Standardpreis pro Lead nach der Testphase
    standard_preis = Column(Float, nullable=False, default=0.0)
    
    # Monatliche Soll-Lead-Anzahl (optional, None = unbegrenzt)
    monatliche_soll_leads = Column(Integer, nullable=True, default=None)
    
    # Rechnungs-Code für Rechnungsnummer (z.B. "LYNR" für LYNR Immobilienwerte GmbH)
    rechnungs_code = Column(String, nullable=True, default=None)
    
    # Notizen für interne Informationen
    notizen = Column(String, nullable=True, default=None)
    
    # Gebiet: Postleitzahlen, kommagetrennt (z.B. "10115, 10117, 10119" oder "10115,10117,10119")
    gebiet = Column(String, nullable=True, default=None)
    
    # GateLink Passwort (optional)
    gatelink_password = Column(String, nullable=True, default=None)
    
    # Vertragspause: Einfaches Boolean-Feld (True = pausiert, False = aktiv)
    vertrag_pausiert = Column(Integer, nullable=False, default=0)  # 0 = nicht pausiert, 1 = pausiert
    
    # Vertrag bis: Datum bis wann der Vertrag läuft (optional, Kündigungsdatum)
    vertrag_bis = Column(Date, nullable=True, default=None)
    
    # Tracking: Wer hat den Makler erstellt/geändert
    created_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    modified_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    
    # Rechnungssystem: "alt" = Monatliche Rechnungen, "neu" = Prepaid-Credits
    rechnungssystem_typ = Column(String, nullable=False, default="alt")
    
    # Erweiterte Preislogik für Credits-System:
    # Erste X Leads im ersten Monat kosten Y€, danach Z€, ab 2. Monat Standard-Preis
    erste_leads_anzahl = Column(Integer, nullable=True, default=5)  # Anzahl der ersten Leads (Standard: 5)
    erste_leads_preis = Column(Float, nullable=True, default=50.0)  # Preis für die ersten X Leads (Standard: 50€)
    erste_leads_danach_preis = Column(Float, nullable=True, default=75.0)  # Preis für Leads über X im 1. Monat (Standard: 75€)
    
    # Optional: Automatische monatliche Aufladung aktivieren
    automatische_aufladung_aktiv = Column(Integer, nullable=False, default=0)  # 0 = deaktiviert, 1 = aktiviert
    automatische_aufladung_betrag = Column(Float, nullable=True)  # Betrag für automatische Aufladung
    automatische_aufladung_tag = Column(Integer, nullable=True)  # Tag des Monats (1-28) für automatische Aufladung


