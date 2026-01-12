from datetime import datetime

from sqlalchemy import Column, DateTime, Float, Integer, String, ForeignKey, Text
from sqlalchemy.orm import relationship

from ..database import Base


class MaklerCredits(Base):
    """
    Repräsentiert eine Credits-Transaktion für einen Makler.
    Positive Beträge = Aufladung, Negative Beträge = Abbuchung (z.B. für Leads).
    """

    __tablename__ = "makler_credits"

    id = Column(Integer, primary_key=True, index=True)
    makler_id = Column(Integer, ForeignKey("makler.id"), nullable=False, index=True)
    
    # Betrag: Positive Werte = Aufladung, Negative = Abbuchung
    betrag = Column(Float, nullable=False)
    
    # Transaktionstyp: "aufladung", "lead_abbuchung", "erstattung", "manuelle_anpassung", "zahlung_online"
    transaktionstyp = Column(String, nullable=False, default="aufladung")
    
    # Optional: Lead-ID bei Lead-Abbuchungen
    lead_id = Column(Integer, ForeignKey("leads.id"), nullable=True, index=True)
    
    # Beschreibung der Transaktion
    beschreibung = Column(Text, nullable=True)
    
    # Zeitstempel
    erstellt_am = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Wer hat die Transaktion erstellt (bei manuellen Aufladungen)
    erstellt_von_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    
    # Optional: Zahlungsreferenz (z.B. Stripe Payment Intent ID)
    zahlungsreferenz = Column(String, nullable=True)
    
    # Optional: Status der Zahlung (bei Online-Zahlungen)
    zahlungsstatus = Column(String, nullable=True)  # "pending", "completed", "failed", "refunded"
    
    makler = relationship("Makler", backref="credits_transaktionen")
    lead = relationship("Lead", foreign_keys=[lead_id], backref="credits_abbuchungen")
    erstellt_von_user = relationship("User", foreign_keys=[erstellt_von_user_id])








