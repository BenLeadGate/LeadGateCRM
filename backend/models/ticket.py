from datetime import datetime, date
from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Date, Enum as SQLEnum
from sqlalchemy.orm import relationship
from enum import Enum as PyEnum

from ..database import Base


class TicketDringlichkeit(str, PyEnum):
    """Dringlichkeit eines Tickets"""
    NIEDRIG = "niedrig"  # Gelb
    MITTEL = "mittel"    # Orange
    HOCH = "hoch"        # Rot


class Ticket(Base):
    """
    Repräsentiert ein Ticket im Ticketing-System.
    Jedes Ticket erstellt automatisch einen neuen Chat.
    """
    
    __tablename__ = "tickets"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Ticket-Informationen
    titel = Column(String, nullable=True)  # Optional: Titel des Tickets
    beschreibung = Column(String, nullable=False)
    fälligkeitsdatum = Column(Date, nullable=True)  # Optional
    dringlichkeit = Column(SQLEnum(TicketDringlichkeit), default=TicketDringlichkeit.MITTEL, nullable=False)
    
    # Erstellt von (nur Admin oder Manager können Tickets erstellen)
    erstellt_von_user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    
    # Chat-Gruppe (jedes Ticket hat einen eigenen Gruppen-Chat)
    chat_gruppe_id = Column(Integer, ForeignKey("chat_gruppen.id", ondelete="SET NULL"), nullable=True, index=True)
    
    # Zeitstempel
    erstellt_am = Column(DateTime, default=datetime.utcnow, nullable=False)
    aktualisiert_am = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Status
    geschlossen = Column(Integer, default=0, nullable=False)  # 0 = offen, 1 = geschlossen
    
    # Relationships
    erstellt_von = relationship("User", foreign_keys=[erstellt_von_user_id], backref="erstellte_tickets")
    teilnehmer = relationship("TicketTeilnehmer", back_populates="ticket", cascade="all, delete-orphan")
    chat_gruppe = relationship("ChatGruppe", foreign_keys=[chat_gruppe_id], backref="ticket")


class TicketTeilnehmer(Base):
    """
    Viele-zu-viele Beziehung zwischen Tickets und Benutzern.
    Definiert, wer Zugriff auf ein Ticket hat.
    """
    
    __tablename__ = "ticket_teilnehmer"
    
    id = Column(Integer, primary_key=True, index=True)
    ticket_id = Column(Integer, ForeignKey("tickets.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Zeitstempel
    hinzugefuegt_am = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    ticket = relationship("Ticket", back_populates="teilnehmer")
    user = relationship("User", backref="ticket_teilnahmen")

