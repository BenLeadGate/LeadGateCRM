from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String

from ..database import Base


class MaklerDokument(Base):
    """
    Repräsentiert ein Dokument (z.B. Vertragsunterlagen) für einen Makler.
    """

    __tablename__ = "makler_dokumente"

    id = Column(Integer, primary_key=True, index=True)
    makler_id = Column(Integer, ForeignKey("makler.id"), nullable=False, index=True)
    dateiname = Column(String, nullable=False)  # Original-Dateiname
    gespeicherter_dateiname = Column(String, nullable=False)  # Name auf dem Server
    hochgeladen_am = Column(DateTime, default=datetime.utcnow, nullable=False)
    hochgeladen_von_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    beschreibung = Column(String, nullable=True)  # Optionale Beschreibung
