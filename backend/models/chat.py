from datetime import datetime

from sqlalchemy import Column, DateTime, Integer, String, ForeignKey, Boolean
from sqlalchemy.orm import relationship

from ..database import Base


class ChatMessage(Base):
    """
    Repräsentiert eine Chat-Nachricht im Postfach-System.
    Unterstützt:
    - User zu User (interne Kommunikation)
    - User zu Makler
    - Makler zu User
    - Gruppen-Chats (für Tickets)
    """
    
    __tablename__ = "chat_messages"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Absender
    from_user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)  # Wer hat die Nachricht gesendet (User)
    from_makler_id = Column(Integer, ForeignKey("makler.id"), nullable=True, index=True)  # Wer hat die Nachricht gesendet (Makler)
    
    # Empfänger (für 1-zu-1 Chats)
    to_user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)  # An wen geht die Nachricht (User)
    to_makler_id = Column(Integer, ForeignKey("makler.id"), nullable=True, index=True)  # An wen geht die Nachricht (Makler)
    
    # Gruppen-Chat (für Tickets)
    chat_gruppe_id = Column(Integer, ForeignKey("chat_gruppen.id", ondelete="CASCADE"), nullable=True, index=True)
    
    nachricht = Column(String, nullable=False)
    erstellt_am = Column(DateTime, default=datetime.utcnow, nullable=False)
    gelesen = Column(Boolean, default=False, nullable=False)  # Ob die Nachricht gelesen wurde
    
    # Relationships
    from_user = relationship("User", foreign_keys=[from_user_id], backref="sent_messages")
    to_user = relationship("User", foreign_keys=[to_user_id], backref="received_messages")
    from_makler = relationship("Makler", foreign_keys=[from_makler_id], backref="sent_messages")
    to_makler = relationship("Makler", foreign_keys=[to_makler_id], backref="received_messages")
    chat_gruppe = relationship("ChatGruppe", foreign_keys=[chat_gruppe_id], back_populates="nachrichten")

