from __future__ import annotations

from datetime import date, datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, EmailStr

# Import UserRole für Schemas - verwende das Enum direkt aus models.user
from .models.user import UserRole


class LeadStatus(str, Enum):
    NEU = "neu"
    UNQUALIFIZIERT = "unqualifiziert"
    QUALIFIZIERT = "qualifiziert"
    GELIEFERT = "geliefert"
    STORNIERT = "storniert"
    FLEXRECALL = "flexrecall"
    NICHT_QUALIFIZIERBAR = "nicht_qualifizierbar"
    REKLAMIERT = "reklamiert"


class MaklerBase(BaseModel):
    firmenname: str
    ansprechpartner: Optional[str] = None
    email: EmailStr
    adresse: Optional[str] = None
    vertragsstart_datum: date
    testphase_leads: int = 0
    testphase_preis: float = 0.0
    standard_preis: float = 0.0
    monatliche_soll_leads: Optional[int] = None
    rechnungs_code: Optional[str] = None
    notizen: Optional[str] = None
    gebiet: Optional[str] = None  # Postleitzahlen, kommagetrennt (z.B. "10115, 10117, 10119")
    gatelink_password: Optional[str] = None  # GateLink Passwort (wird nicht zurückgegeben)
    vertrag_pausiert: int = 0  # 0 = nicht pausiert, 1 = pausiert
    vertrag_bis: Optional[date] = None  # Vertrag läuft bis (Kündigungsdatum)
    # Credits-System
    rechnungssystem_typ: str = "alt"  # "alt" = Monatliche Rechnungen, "neu" = Prepaid-Credits
    erste_leads_anzahl: Optional[int] = 5  # Anzahl der ersten Leads (Standard: 5)
    erste_leads_preis: Optional[float] = 50.0  # Preis für die ersten X Leads (Standard: 50€)
    erste_leads_danach_preis: Optional[float] = 75.0  # Preis für Leads über X im 1. Monat (Standard: 75€)
    automatische_aufladung_aktiv: int = 0  # 0 = deaktiviert, 1 = aktiviert
    automatische_aufladung_betrag: Optional[float] = None  # Betrag für automatische Aufladung
    automatische_aufladung_tag: Optional[int] = None  # Tag des Monats (1-28) für automatische Aufladung


class MaklerCreate(MaklerBase):
    pass  # Alle Felder sind bereits in MaklerBase


class MaklerUpdate(BaseModel):
    firmenname: Optional[str] = None
    ansprechpartner: Optional[str] = None
    email: Optional[EmailStr] = None
    adresse: Optional[str] = None
    vertragsstart_datum: Optional[date] = None
    testphase_leads: Optional[int] = None
    testphase_preis: Optional[float] = None
    standard_preis: Optional[float] = None
    monatliche_soll_leads: Optional[int] = None
    rechnungs_code: Optional[str] = None
    notizen: Optional[str] = None
    gebiet: Optional[str] = None  # Postleitzahlen, kommagetrennt
    gatelink_password: Optional[str] = None  # GateLink Passwort
    vertrag_pausiert: Optional[int] = None  # 0 = nicht pausiert, 1 = pausiert
    vertrag_bis: Optional[date] = None  # Vertrag läuft bis (Kündigungsdatum)
    # Credits-System
    rechnungssystem_typ: Optional[str] = None  # "alt" = Monatliche Rechnungen, "neu" = Prepaid-Credits
    erste_leads_anzahl: Optional[int] = None  # Anzahl der ersten Leads
    erste_leads_preis: Optional[float] = None  # Preis für die ersten X Leads
    erste_leads_danach_preis: Optional[float] = None  # Preis für Leads über X im 1. Monat
    automatische_aufladung_aktiv: Optional[int] = None  # 0 = deaktiviert, 1 = aktiviert
    automatische_aufladung_betrag: Optional[float] = None  # Betrag für automatische Aufladung
    automatische_aufladung_tag: Optional[int] = None  # Tag des Monats (1-28) für automatische Aufladung


class MaklerRead(MaklerBase):
    id: int
    # gatelink_password wird aus Sicherheitsgründen nicht zurückgegeben

    class Config:
        from_attributes = True


class LeadBase(BaseModel):
    lead_nummer: Optional[int] = None  # Eindeutige Lead-Nummer
    makler_id: Optional[int] = None
    # Neue Leads haben standardmäßig den Status "unqualifiziert" und sind keinem Makler zugeordnet
    status: LeadStatus = LeadStatus.UNQUALIFIZIERT
    erstellt_am: Optional[datetime] = None
    # Lead-Details
    anbieter_name: Optional[str] = None
    postleitzahl: Optional[str] = None
    ort: Optional[str] = None
    grundstuecksflaeche: Optional[float] = None
    wohnflaeche: Optional[float] = None
    preis: Optional[float] = None
    telefonnummer: Optional[str] = None
    features: Optional[str] = None
    immobilien_typ: Optional[str] = None  # z.B. "Eigentumswohnung", "Haus", "Grundstück"
    baujahr: Optional[int] = None  # Baujahr der Immobilie
    lage: Optional[str] = None  # Lagebeschreibung (z.B. "Ruhige Lage", "Zentrumsnah")
    beschreibung: Optional[str] = None  # Beschreibung/Notizen vom Telefonisten
    moegliche_makler_ids: Optional[str] = None  # Kommagetrennte Liste von Makler-IDs, die für diese PLZ zuständig sind
    kontakt_datum: Optional[date] = None  # Datum, an dem der Makler den Lead kontaktieren kann
    kontakt_zeitraum: Optional[str] = None  # Zeitspanne, z.B. "14:00 - 16:00"
    qualifiziert_am: Optional[datetime] = None  # Datum/Zeit, wann der Lead qualifiziert wurde
    # Makler-spezifische Felder
    makler_status: Optional[str] = None  # Status vom Makler (in_gespraechen, erstkontakt, nicht_funktioniert, reklamation, unter_vertrag, verkauft)
    makler_beschreibung: Optional[str] = None  # Beschreibung/Notizen vom Makler
    makler_status_geaendert_am: Optional[datetime] = None  # Wann wurde der Status zuletzt geändert
    telefon_kontakt_ergebnis: Optional[str] = None  # Ergebnis des Telefonkontakts: erreicht, nicht_erreicht, rueckruf
    telefon_kontakt_datum: Optional[date] = None  # Datum des Telefonkontakts
    telefon_kontakt_uhrzeit: Optional[str] = None  # Uhrzeit des Telefonkontakts
    # Checklisten-Felder
    termin_vereinbart: Optional[int] = None
    termin_ort: Optional[str] = None
    termin_datum: Optional[date] = None
    termin_uhrzeit: Optional[str] = None
    termin_notiz: Optional[str] = None
    absage: Optional[int] = None
    absage_notiz: Optional[str] = None
    zweit_termin_vereinbart: Optional[int] = None
    zweit_termin_ort: Optional[str] = None
    zweit_termin_datum: Optional[date] = None
    zweit_termin_uhrzeit: Optional[str] = None
    zweit_termin_notiz: Optional[str] = None
    maklervertrag_unterschrieben: Optional[int] = None
    maklervertrag_notiz: Optional[str] = None
    immobilie_verkauft: Optional[int] = None
    immobilie_verkauft_datum: Optional[date] = None
    immobilie_verkauft_preis: Optional[str] = None
    beteiligungs_prozent: Optional[float] = None  # Prozentuale Beteiligung am Verkaufspreis
    favorit: Optional[int] = None  # 0 oder 1 (Boolean) - Favoriten-Markierung
    makler_angesehen: Optional[int] = None  # 0 oder 1 (Boolean) - Wurde der Lead vom Makler bereits geöffnet


class LeadCreate(LeadBase):
    pass


class LeadUpdate(BaseModel):
    status: Optional[LeadStatus] = None
    makler_id: Optional[int] = None  # Makler-Zuordnung
    anbieter_name: Optional[str] = None  # Eigentümer/Anbieter Name (bearbeitbar)
    beschreibung: Optional[str] = None  # Telefonisten können Beschreibungen hinzufügen
    preis: Optional[float] = None  # Preis des Leads
    kontakt_datum: Optional[date] = None  # Datum, an dem der Makler den Lead kontaktieren kann
    kontakt_zeitraum: Optional[str] = None  # Zeitspanne, z.B. "14:00 - 16:00"
    ohne_credits_qualifizieren: Optional[bool] = False  # Wenn True, wird Lead qualifiziert ohne Credits abzubuchen (nur wenn nicht genug Credits vorhanden)
    # Makler-spezifische Felder
    makler_status: Optional[str] = None  # Status vom Makler
    makler_beschreibung: Optional[str] = None  # Beschreibung vom Makler
    telefon_kontakt_ergebnis: Optional[str] = None  # Ergebnis des Telefonkontakts: erreicht, nicht_erreicht, rueckruf
    telefon_kontakt_datum: Optional[date] = None  # Datum des Telefonkontakts
    telefon_kontakt_uhrzeit: Optional[str] = None  # Uhrzeit des Telefonkontakts
    # Checklisten-Felder
    termin_vereinbart: Optional[int] = None
    termin_ort: Optional[str] = None
    termin_datum: Optional[date] = None
    termin_uhrzeit: Optional[str] = None
    termin_notiz: Optional[str] = None
    absage: Optional[int] = None
    absage_notiz: Optional[str] = None
    zweit_termin_vereinbart: Optional[int] = None
    zweit_termin_ort: Optional[str] = None
    zweit_termin_datum: Optional[date] = None
    zweit_termin_uhrzeit: Optional[str] = None
    zweit_termin_notiz: Optional[str] = None
    maklervertrag_unterschrieben: Optional[int] = None
    maklervertrag_notiz: Optional[str] = None
    immobilie_verkauft: Optional[int] = None
    immobilie_verkauft_datum: Optional[date] = None
    immobilie_verkauft_preis: Optional[str] = None
    beteiligungs_prozent: Optional[float] = None  # Prozentuale Beteiligung am Verkaufspreis
    favorit: Optional[int] = None  # 0 oder 1 (Boolean) - Favoriten-Markierung
    makler_angesehen: Optional[int] = None  # 0 oder 1 (Boolean) - Wurde der Lead vom Makler bereits geöffnet


class LeadRead(LeadBase):
    id: int
    qualifiziert_von_user_id: Optional[int] = None
    qualifiziert_von_username: Optional[str] = None  # Username des Users, der den Lead qualifiziert hat

    class Config:
        from_attributes = True


class RechnungBase(BaseModel):
    makler_id: int
    rechnungstyp: str = "monatlich"  # "monatlich" oder "beteiligung"
    monat: Optional[int] = None
    jahr: Optional[int] = None
    anzahl_leads: Optional[int] = None
    preis_pro_lead: Optional[float] = None
    lead_id: Optional[int] = None
    verkaufspreis: Optional[float] = None
    beteiligungs_prozent: Optional[float] = None
    netto_betrag: Optional[float] = None
    gesamtbetrag: float
    erstellt_am: Optional[datetime] = None
    status: str = "offen"  # offen, überfällig, bezahlt, zahlungserinnerung_gesendet, mahnung_1, mahnung_2, mahnverfahren


class RechnungRead(RechnungBase):
    id: int

    class Config:
        from_attributes = True


class MonatsabrechnungRequest(BaseModel):
    monat: int
    jahr: int


class BeteiligungsabrechnungRequest(BaseModel):
    lead_id: int


class RechnungStatusUpdate(BaseModel):
    status: str  # offen, überfällig, bezahlt, zahlungserinnerung_gesendet, mahnung_1, mahnung_2, mahnverfahren


# User-Schemas für Authentifizierung
# UserRole wird aus models.user importiert
from .models.user import UserRole


class UserBase(BaseModel):
    username: str
    email: EmailStr


class UserCreate(UserBase):
    password: str


class UserCreateSimple(BaseModel):
    """Schema für einfache Benutzer-Erstellung (nur für eingeloggte Benutzer)"""
    username: str
    password: str
    email: Optional[EmailStr] = None  # Optional, wird automatisch generiert falls nicht angegeben
    role: Optional[UserRole] = UserRole.TELEFONIST  # Standard-Rolle


class UserRead(UserBase):
    id: int
    is_active: bool
    role: UserRole
    created_at: datetime

    class Config:
        from_attributes = True


class UserUpdate(BaseModel):
    """Schema für Benutzer-Updates (nur Admin)"""
    role: Optional[UserRole] = None
    is_active: Optional[bool] = None


class UserLogin(BaseModel):
    username: str
    password: str


class Token(BaseModel):
    access_token: str
    refresh_token: Optional[str] = None
    token_type: str


class TokenData(BaseModel):
    username: Optional[str] = None


# Chat-Schemas
class ChatMessageBase(BaseModel):
    nachricht: str


class ChatMessageCreate(ChatMessageBase):
    to_user_id: Optional[int] = None  # An welchen User (für User-zu-User oder User-zu-Makler)
    to_makler_id: Optional[int] = None  # An welchen Makler (für User-zu-Makler oder Makler-zu-User)
    chat_gruppe_id: Optional[int] = None  # Für Gruppen-Chats (z.B. Tickets)


class ChatMessageRead(ChatMessageBase):
    id: int
    from_user_id: Optional[int] = None
    from_makler_id: Optional[int] = None
    to_user_id: Optional[int] = None
    to_makler_id: Optional[int] = None
    chat_gruppe_id: Optional[int] = None
    erstellt_am: datetime
    gelesen: bool
    from_user_username: Optional[str] = None
    from_makler_firmenname: Optional[str] = None
    to_user_username: Optional[str] = None
    chat_gruppe_name: Optional[str] = None
    to_makler_firmenname: Optional[str] = None
    
    class Config:
        from_attributes = True


class ConversationSummary(BaseModel):
    """Zusammenfassung einer Konversation für die Postfach-Ansicht"""
    contact_id: int  # ID des Kontakts (User-ID, Makler-ID oder Chat-Gruppen-ID)
    contact_type: str  # "user", "makler" oder "gruppe"
    contact_name: str  # Name des Kontakts oder der Gruppe
    last_message: Optional[str] = None
    last_message_time: Optional[datetime] = None
    unread_count: int = 0
    is_gruppe: bool = False  # True wenn es eine Gruppen-Chat ist


# Credits-System Schemas
class MaklerCreditsBase(BaseModel):
    betrag: float
    transaktionstyp: str = "aufladung"  # "aufladung", "lead_abbuchung", "erstattung", "manuelle_anpassung", "zahlung_online"
    lead_id: Optional[int] = None
    beschreibung: Optional[str] = None
    zahlungsreferenz: Optional[str] = None
    zahlungsstatus: Optional[str] = None  # "pending", "completed", "failed", "refunded"


class MaklerCreditsCreate(MaklerCreditsBase):
    makler_id: int


class MaklerCreditsRead(MaklerCreditsBase):
    id: int
    makler_id: int
    erstellt_am: datetime
    erstellt_von_user_id: Optional[int] = None

    class Config:
        from_attributes = True


class MaklerCreditsAufladen(BaseModel):
    betrag: float
    beschreibung: Optional[str] = None


class MaklerCreditsStand(BaseModel):
    """Aktueller Credits-Stand eines Maklers"""
    makler_id: int
    aktueller_stand: float  # Summe aller Transaktionen
    letzte_transaktion_am: Optional[datetime] = None
    transaktionsanzahl: int = 0


class CreditsRueckzahlungRequest(BaseModel):
    """Anfrage für Credits-Rückzahlung"""
    transaktion_id: int  # ID der ursprünglichen Aufladungs-Transaktion
    betrag: float  # Betrag der zurückgezahlt werden soll
    beschreibung: Optional[str] = None


class CreditsRueckzahlungAnfrageCreate(BaseModel):
    """Erstelle eine Rückzahlungsanfrage"""
    transaktion_id: int
    betrag: float
    beschreibung: Optional[str] = None


class CreditsRueckzahlungAnfrageRead(BaseModel):
    """Rückzahlungsanfrage-Daten"""
    id: int
    makler_id: int
    transaktion_id: int
    betrag: float
    status: str  # "pending", "approved", "rejected"
    beschreibung: Optional[str] = None
    erstellt_am: datetime
    bearbeitet_am: Optional[datetime] = None
    bearbeitet_von_user_id: Optional[int] = None
    rueckzahlung_transaktion_id: Optional[int] = None
    rueckzahlung_status: Optional[str] = None  # "zurueckzuzahlen", "zurueckgezahlt", "stripe_refund_pending", "stripe_refund_completed"
    stripe_refund_id: Optional[str] = None
    makler_firmenname: Optional[str] = None
    bearbeitet_von_username: Optional[str] = None
    
    class Config:
        from_attributes = True


class CreditsRueckzahlungAnfrageBearbeitung(BaseModel):
    """Bearbeitung einer Rückzahlungsanfrage (Genehmigung/Ablehnung)"""
    anfrage_id: int
    status: str  # "approved" oder "rejected"
    beschreibung: Optional[str] = None  # Optional: Begründung


# Ticket-Schemas
from .models.ticket import TicketDringlichkeit


class TicketBase(BaseModel):
    titel: Optional[str] = None  # Optional: Titel des Tickets
    beschreibung: str
    fälligkeitsdatum: Optional[date] = None
    dringlichkeit: TicketDringlichkeit = TicketDringlichkeit.MITTEL
    teilnehmer_ids: list[int] = []  # Liste der User-IDs, die Zugriff auf das Ticket haben


class TicketCreate(TicketBase):
    pass


class TicketRead(TicketBase):
    id: int
    erstellt_von_user_id: int
    erstellt_von_username: Optional[str] = None
    chat_id: Optional[int] = None  # Alias für chat_gruppe_id (für Kompatibilität)
    chat_gruppe_id: Optional[int] = None
    erstellt_am: datetime
    aktualisiert_am: datetime
    geschlossen: bool = False
    teilnehmer: list[dict] = []  # Liste der Teilnehmer mit Username
    
    class Config:
        from_attributes = True


class TicketUpdate(BaseModel):
    titel: Optional[str] = None
    beschreibung: Optional[str] = None
    fälligkeitsdatum: Optional[date] = None
    dringlichkeit: Optional[TicketDringlichkeit] = None
    geschlossen: Optional[bool] = None


class TicketTeilnehmerHinzufuegen(BaseModel):
    user_ids: list[int]  # Liste der User-IDs, die hinzugefügt werden sollen


