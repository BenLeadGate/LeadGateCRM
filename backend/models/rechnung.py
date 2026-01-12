from datetime import datetime

from sqlalchemy import Column, DateTime, Float, Integer, String, ForeignKey
from sqlalchemy.orm import relationship

from ..database import Base


class Rechnung(Base):
    """
    Repräsentiert eine monatliche Abrechnung oder eine Beteiligungsabrechnung für einen Makler.
    """

    __tablename__ = "rechnungen"

    id = Column(Integer, primary_key=True, index=True)
    makler_id = Column(Integer, ForeignKey("makler.id"), nullable=False, index=True)
    rechnungstyp = Column(String, nullable=False, default="monatlich")  # "monatlich" oder "beteiligung"
    
    # Felder für Monatsabrechnung
    monat = Column(Integer, nullable=True)  # 1-12 (nur bei monatlich)
    jahr = Column(Integer, nullable=True)  # nur bei monatlich
    anzahl_leads = Column(Integer, nullable=True)  # nur bei monatlich
    preis_pro_lead = Column(Float, nullable=True)  # nur bei monatlich
    
    # Felder für Beteiligungsabrechnung
    lead_id = Column(Integer, ForeignKey("leads.id"), nullable=True, index=True)  # nur bei beteiligung
    verkaufspreis = Column(Float, nullable=True)  # nur bei beteiligung
    beteiligungs_prozent = Column(Float, nullable=True)  # nur bei beteiligung
    netto_betrag = Column(Float, nullable=True)  # nur bei beteiligung (Verkaufspreis * Beteiligungsprozentsatz)
    
    # Gemeinsame Felder
    gesamtbetrag = Column(Float, nullable=False)  # Brutto-Gesamtbetrag (inkl. MwSt)
    
    erstellt_am = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Status der Rechnung
    status = Column(String, nullable=False, default="offen")  # offen, überfällig, bezahlt, zahlungserinnerung_gesendet, mahnung_1, mahnung_2, mahnverfahren
    
    # Tracking: Wer hat die Rechnung erstellt
    created_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)

    makler = relationship("Makler", backref="rechnungen")
    lead = relationship("Lead", foreign_keys=[lead_id], backref="beteiligungsrechnungen")



