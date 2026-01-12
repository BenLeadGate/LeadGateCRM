from datetime import datetime

from sqlalchemy import Column, DateTime, Float, Integer, String, ForeignKey, Text
from sqlalchemy.orm import relationship

from ..database import Base


class CreditsRueckzahlungAnfrage(Base):
    """
    Repräsentiert eine Rückzahlungsanfrage von einem Makler.
    """
    
    __tablename__ = "credits_rueckzahlung_anfragen"
    
    id = Column(Integer, primary_key=True, index=True)
    makler_id = Column(Integer, ForeignKey("makler.id"), nullable=False, index=True)
    
    # Welche Transaktion soll zurückgezahlt werden
    transaktion_id = Column(Integer, ForeignKey("makler_credits.id"), nullable=False)
    
    # Betrag der zurückgezahlt werden soll
    betrag = Column(Float, nullable=False)
    
    # Status: "pending", "approved", "rejected"
    status = Column(String, nullable=False, default="pending", index=True)
    
    # Beschreibung/Notizen
    beschreibung = Column(Text, nullable=True)
    
    # Zeitstempel
    erstellt_am = Column(DateTime, default=datetime.utcnow, nullable=False)
    bearbeitet_am = Column(DateTime, nullable=True)
    
    # Wer hat die Anfrage bearbeitet (Admin/Manager)
    bearbeitet_von_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    
    # Optional: Referenz zur Rückzahlungs-Transaktion (wenn genehmigt)
    rueckzahlung_transaktion_id = Column(Integer, ForeignKey("makler_credits.id"), nullable=True)
    
    # Status der tatsächlichen Rückzahlung: "zurueckzuzahlen", "zurueckgezahlt", "stripe_refund_pending", "stripe_refund_completed"
    rueckzahlung_status = Column(String, nullable=True, default="zurueckzuzahlen")  # Nur wenn status="approved"
    
    # Optional: Stripe Refund ID (wenn über Stripe zurückgezahlt)
    stripe_refund_id = Column(String, nullable=True)
    
    # Relationships
    makler = relationship("Makler", backref="rueckzahlung_anfragen")
    transaktion = relationship("MaklerCredits", foreign_keys=[transaktion_id])
    rueckzahlung_transaktion = relationship("MaklerCredits", foreign_keys=[rueckzahlung_transaktion_id])
    bearbeitet_von_user = relationship("User", backref="bearbeitete_rueckzahlung_anfragen")

