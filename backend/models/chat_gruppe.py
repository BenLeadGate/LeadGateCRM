from datetime import datetime
from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Boolean
from sqlalchemy.orm import relationship

from ..database import Base


class ChatGruppe(Base):
    """
    Repräsentiert eine Chat-Gruppe (z.B. für Tickets).
    Gruppen können mehrere Teilnehmer haben.
    """
    
    __tablename__ = "chat_gruppen"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Gruppen-Informationen
    name = Column(String, nullable=False)  # Name der Gruppe (z.B. "Ticket #123")
    beschreibung = Column(String, nullable=True)  # Optional: Beschreibung
    
    # Erstellt von
    erstellt_von_user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    
    # Zeitstempel
    erstellt_am = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    erstellt_von = relationship("User", foreign_keys=[erstellt_von_user_id], backref="erstellte_chat_gruppen")
    teilnehmer = relationship("ChatGruppeTeilnehmer", back_populates="gruppe", cascade="all, delete-orphan")
    nachrichten = relationship("ChatMessage", back_populates="chat_gruppe", cascade="all, delete-orphan")


class ChatGruppeTeilnehmer(Base):
    """
    Viele-zu-viele Beziehung zwischen Chat-Gruppen und Benutzern.
    Definiert, wer Mitglied einer Chat-Gruppe ist.
    """
    
    __tablename__ = "chat_gruppe_teilnehmer"
    
    id = Column(Integer, primary_key=True, index=True)
    chat_gruppe_id = Column(Integer, ForeignKey("chat_gruppen.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Zeitstempel
    hinzugefuegt_am = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    gruppe = relationship("ChatGruppe", back_populates="teilnehmer")
    user = relationship("User", backref="chat_gruppen_teilnahmen")


