from datetime import datetime, date

from sqlalchemy import Column, DateTime, Date, Enum, ForeignKey, Integer, String, Float, Text
from sqlalchemy.orm import relationship

from ..database import Base


class LeadStatusEnum(str):
    NEU = "neu"
    UNQUALIFIZIERT = "unqualifiziert"
    QUALIFIZIERT = "qualifiziert"
    GELIEFERT = "geliefert"
    STORNIERT = "storniert"
    FLEXRECALL = "flexrecall"
    NICHT_QUALIFIZIERBAR = "nicht_qualifizierbar"
    REKLAMIERT = "reklamiert"


class Lead(Base):
    """
    Repräsentiert einen Lead, der einem Makler zugeordnet ist.
    """

    __tablename__ = "leads"

    id = Column(Integer, primary_key=True, index=True)
    lead_nummer = Column(Integer, nullable=True, unique=True, index=True)  # Eindeutige Lead-Nummer (fortlaufend)
    makler_id = Column(Integer, ForeignKey("makler.id"), nullable=True, index=True)
    erstellt_am = Column(DateTime, default=datetime.utcnow, nullable=False)
    status = Column(
        Enum(
            LeadStatusEnum.NEU,
            LeadStatusEnum.UNQUALIFIZIERT,
            LeadStatusEnum.QUALIFIZIERT,
            LeadStatusEnum.GELIEFERT,
            LeadStatusEnum.STORNIERT,
            LeadStatusEnum.FLEXRECALL,
            LeadStatusEnum.NICHT_QUALIFIZIERBAR,
            LeadStatusEnum.REKLAMIERT,
            name="lead_status",
        ),
        default=LeadStatusEnum.UNQUALIFIZIERT,
        nullable=False,
    )
    
    # Tracking: Wer hat den Lead erstellt
    created_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    
    # Lead-Details
    anbieter_name = Column(String, nullable=True)  # Name des Anbieters (Makler)
    postleitzahl = Column(String, nullable=True)
    ort = Column(String, nullable=True)
    grundstuecksflaeche = Column(Float, nullable=True)  # in m²
    wohnflaeche = Column(Float, nullable=True)  # in m²
    preis = Column(Float, nullable=True)  # Preis in Euro
    telefonnummer = Column(String, nullable=True)
    features = Column(String, nullable=True)  # Keller, Balkon, Garten etc. (kommagetrennt oder JSON)
    immobilien_typ = Column(String, nullable=True)  # z.B. "Eigentumswohnung", "Haus", "Grundstück"
    baujahr = Column(Integer, nullable=True)  # Baujahr der Immobilie
    lage = Column(String, nullable=True)  # Lagebeschreibung (z.B. "Ruhige Lage", "Zentrumsnah")
    beschreibung = Column(Text, nullable=True)  # Beschreibung/Notizen vom Telefonisten (unbegrenzte Länge)
    moegliche_makler_ids = Column(String, nullable=True)  # Kommagetrennte Liste von Makler-IDs, die für diese PLZ zuständig sind (z.B. "1, 3, 5")
    kontakt_datum = Column(Date, nullable=True)  # Datum, an dem der Makler den Lead kontaktieren kann
    kontakt_zeitraum = Column(String, nullable=True)  # Zeitspanne, z.B. "14:00 - 16:00"
    qualifiziert_am = Column(DateTime, nullable=True)  # Datum/Zeit, wann der Lead qualifiziert wurde (zählt ab diesem Zeitpunkt für den Makler)
    qualifiziert_von_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)  # Wer hat den Lead qualifiziert
    
    # Locking-System für Telefonisten (verhindert, dass mehrere Telefonisten gleichzeitig am selben Lead arbeiten)
    bearbeitet_von_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)  # Welcher Telefonist bearbeitet gerade diesen Lead
    bearbeitet_seit = Column(DateTime, nullable=True)  # Seit wann wird der Lead bearbeitet (für Timeout)
    
    # Makler-spezifische Felder für GateLink
    makler_status = Column(String, nullable=True)  # Status vom Makler gesetzt (in_gespraechen, erstkontakt, nicht_funktioniert, reklamation, unter_vertrag, verkauft)
    makler_beschreibung = Column(Text, nullable=True)  # Beschreibung/Notizen vom Makler (unbegrenzte Länge)
    makler_status_geaendert_am = Column(DateTime, nullable=True)  # Wann wurde der Status zuletzt geändert
    telefon_kontakt_ergebnis = Column(String, nullable=True)  # Ergebnis des Telefonkontakts: erreicht, nicht_erreicht, rueckruf
    telefon_kontakt_datum = Column(Date, nullable=True)  # Datum des Telefonkontakts
    telefon_kontakt_uhrzeit = Column(String, nullable=True)  # Uhrzeit des Telefonkontakts (z.B. "14:30")
    # Checklisten-Felder
    termin_vereinbart = Column(Integer, nullable=True, default=0)  # 0 oder 1 (Boolean)
    termin_ort = Column(String, nullable=True)
    termin_datum = Column(Date, nullable=True)
    termin_uhrzeit = Column(String, nullable=True)
    termin_notiz = Column(Text, nullable=True)
    absage = Column(Integer, nullable=True, default=0)  # 0 oder 1 (Boolean)
    absage_notiz = Column(Text, nullable=True)
    zweit_termin_vereinbart = Column(Integer, nullable=True, default=0)  # 0 oder 1 (Boolean)
    zweit_termin_ort = Column(String, nullable=True)
    zweit_termin_datum = Column(Date, nullable=True)
    zweit_termin_uhrzeit = Column(String, nullable=True)
    zweit_termin_notiz = Column(Text, nullable=True)
    maklervertrag_unterschrieben = Column(Integer, nullable=True, default=0)  # 0 oder 1 (Boolean)
    maklervertrag_notiz = Column(Text, nullable=True)
    immobilie_verkauft = Column(Integer, nullable=True, default=0)  # 0 oder 1 (Boolean)
    immobilie_verkauft_datum = Column(Date, nullable=True)  # Datum des Verkaufs
    immobilie_verkauft_preis = Column(String, nullable=True)  # Verkaufspreis
    beteiligungs_prozent = Column(Float, nullable=True)  # Prozentuale Beteiligung am Verkaufspreis (z.B. 3.5 für 3.5%)
    favorit = Column(Integer, nullable=True, default=0)  # 0 oder 1 (Boolean) - Favoriten-Markierung für Makler
    makler_angesehen = Column(Integer, nullable=True, default=0)  # 0 oder 1 (Boolean) - Wurde der Lead vom Makler bereits geöffnet/angesehen
    
    makler = relationship("Makler", backref="leads")
    qualifiziert_von_user = relationship("User", foreign_keys=[qualifiziert_von_user_id], backref="qualifizierte_leads")



