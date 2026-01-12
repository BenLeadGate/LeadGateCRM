from datetime import datetime, date
from typing import List, Optional
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import or_, and_
from fastapi import APIRouter, Depends, HTTPException, status

from ..database import get_db
from ..models import User, Ticket, TicketTeilnehmer, TicketDringlichkeit, ChatMessage, ChatGruppe, ChatGruppeTeilnehmer, ChatGruppe, ChatGruppeTeilnehmer
from ..models.user import UserRole
from ..schemas import TicketCreate, TicketRead, TicketUpdate, TicketTeilnehmerHinzufuegen
from ..routers.auth import get_current_active_user, require_admin_or_manager

router = APIRouter(prefix="/tickets", tags=["tickets"])


def require_admin_or_manager_for_tickets(current_user: User = Depends(get_current_active_user)):
    """Prüft, ob der Benutzer Admin oder Manager ist (nur diese können Tickets erstellen)"""
    if current_user.role not in [UserRole.ADMIN, UserRole.MANAGER]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Nur Admin und Manager können Tickets erstellen"
        )
    return current_user


def kann_user_ticket_sehen(ticket: Ticket, user: User, db: Session) -> bool:
    """Prüft, ob ein Benutzer Zugriff auf ein Ticket hat"""
    # Ersteller kann immer sehen
    if ticket.erstellt_von_user_id == user.id:
        return True
    
    # Prüfe, ob Benutzer als Teilnehmer markiert ist
    teilnahme = db.query(TicketTeilnehmer).filter(
        and_(
            TicketTeilnehmer.ticket_id == ticket.id,
            TicketTeilnehmer.user_id == user.id
        )
    ).first()
    
    return teilnahme is not None


@router.post("", response_model=TicketRead, status_code=status.HTTP_201_CREATED)
def erstelle_ticket(
    ticket_data: TicketCreate,
    current_user: User = Depends(require_admin_or_manager_for_tickets),
    db: Session = Depends(get_db)
):
    """
    Erstellt ein neues Ticket.
    Nur Admin und Manager können Tickets erstellen.
    Erstellt automatisch einen neuen Chat für das Ticket.
    """
    # Prüfe, dass alle Teilnehmer interne Benutzer sind (keine Makler)
    if ticket_data.teilnehmer_ids:
        teilnehmer_users = db.query(User).filter(User.id.in_(ticket_data.teilnehmer_ids)).all()
        if len(teilnehmer_users) != len(ticket_data.teilnehmer_ids):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Ein oder mehrere Teilnehmer wurden nicht gefunden"
            )
    
    # Erstelle Ticket
    ticket = Ticket(
        titel=ticket_data.titel,
        beschreibung=ticket_data.beschreibung,
        fälligkeitsdatum=ticket_data.fälligkeitsdatum,
        dringlichkeit=ticket_data.dringlichkeit,
        erstellt_von_user_id=current_user.id
    )
    
    db.add(ticket)
    db.flush()  # Um die ID zu erhalten
    
    # Füge Teilnehmer hinzu (inklusive Ersteller)
    teilnehmer_ids = set(ticket_data.teilnehmer_ids)
    teilnehmer_ids.add(current_user.id)  # Ersteller ist immer Teilnehmer
    
    for user_id in teilnehmer_ids:
        teilnehmer = TicketTeilnehmer(
            ticket_id=ticket.id,
            user_id=user_id
        )
        db.add(teilnehmer)
    
    # Erstelle eine Chat-Gruppe für das Ticket
    chat_gruppe_name = ticket.titel if ticket.titel else f"Ticket #{ticket.id}"
    chat_gruppe = ChatGruppe(
        name=chat_gruppe_name,
        beschreibung=ticket.beschreibung[:100] if ticket.beschreibung else None,  # Erste 100 Zeichen
        erstellt_von_user_id=current_user.id
    )
    db.add(chat_gruppe)
    db.flush()  # Um die ID zu erhalten
    
    # Füge alle Teilnehmer zur Chat-Gruppe hinzu
    for user_id in teilnehmer_ids:
        gruppe_teilnehmer = ChatGruppeTeilnehmer(
            chat_gruppe_id=chat_gruppe.id,
            user_id=user_id
        )
        db.add(gruppe_teilnehmer)
    
    # Lade Teilnehmer-Namen für die Nachricht
    teilnehmer_namen = []
    for user_id in teilnehmer_ids:
        user = db.query(User).filter(User.id == user_id).first()
        if user:
            teilnehmer_namen.append(user.username)
    
    # Erstelle die erste Nachricht in der Chat-Gruppe
    ticket_nachricht = f"🎫 **Neues Ticket #{ticket.id}**\n\n"
    if ticket.titel:
        ticket_nachricht += f"**Titel:** {ticket.titel}\n"
    ticket_nachricht += f"**Beschreibung:** {ticket.beschreibung}\n"
    if ticket.fälligkeitsdatum:
        ticket_nachricht += f"**Fälligkeitsdatum:** {ticket.fälligkeitsdatum.strftime('%d.%m.%Y')}\n"
    ticket_nachricht += f"**Dringlichkeit:** {ticket.dringlichkeit.value.upper()}\n"
    ticket_nachricht += f"**Erstellt von:** {current_user.username}\n"
    ticket_nachricht += f"**Teilnehmer:** {', '.join(teilnehmer_namen)}\n"
    
    # Erstelle Chat-Nachricht in der Gruppe
    chat_message = ChatMessage(
        from_user_id=current_user.id,
        chat_gruppe_id=chat_gruppe.id,
        nachricht=ticket_nachricht,
        gelesen=False
    )
    db.add(chat_message)
    
    # Verknüpfe Ticket mit Chat-Gruppe
    ticket.chat_gruppe_id = chat_gruppe.id
    
    db.commit()
    db.refresh(ticket)
    
    # Lade Ticket-Details für Response
    return lade_ticket_details(ticket, db)


@router.get("", response_model=List[TicketRead])
def get_tickets(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Gibt alle Tickets zurück, auf die der aktuelle Benutzer Zugriff hat.
    """
    # Finde alle Tickets, bei denen der Benutzer Teilnehmer ist oder Ersteller
    ticket_ids = db.query(TicketTeilnehmer.ticket_id).filter(
        TicketTeilnehmer.user_id == current_user.id
    ).all()
    ticket_ids = [t[0] for t in ticket_ids]
    
    # Füge Tickets hinzu, die der Benutzer erstellt hat
    erstellte_tickets = db.query(Ticket.id).filter(
        Ticket.erstellt_von_user_id == current_user.id
    ).all()
    ticket_ids.extend([t[0] for t in erstellte_tickets])
    
    # Entferne Duplikate
    ticket_ids = list(set(ticket_ids))
    
    if not ticket_ids:
        return []
    
    # Lade alle Tickets mit Teilnehmern
    tickets = db.query(Ticket).options(
        joinedload(Ticket.teilnehmer).joinedload(TicketTeilnehmer.user),
        joinedload(Ticket.erstellt_von)
    ).filter(Ticket.id.in_(ticket_ids)).order_by(Ticket.erstellt_am.desc()).all()
    
    return [lade_ticket_details(ticket, db) for ticket in tickets]


@router.get("/{ticket_id}", response_model=TicketRead)
def get_ticket(
    ticket_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Gibt ein spezifisches Ticket zurück.
    Nur Teilnehmer oder Ersteller können das Ticket sehen.
    """
    ticket = db.query(Ticket).options(
        joinedload(Ticket.teilnehmer).joinedload(TicketTeilnehmer.user),
        joinedload(Ticket.erstellt_von)
    ).filter(Ticket.id == ticket_id).first()
    
    if not ticket:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ticket nicht gefunden"
        )
    
    # Prüfe Berechtigung
    if not kann_user_ticket_sehen(ticket, current_user, db):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Sie haben keinen Zugriff auf dieses Ticket"
        )
    
    return lade_ticket_details(ticket, db)


@router.put("/{ticket_id}", response_model=TicketRead)
def update_ticket(
    ticket_id: int,
    ticket_update: TicketUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Aktualisiert ein Ticket.
    Nur Teilnehmer können das Ticket aktualisieren.
    """
    ticket = db.query(Ticket).filter(Ticket.id == ticket_id).first()
    
    if not ticket:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ticket nicht gefunden"
        )
    
    # Prüfe Berechtigung
    if not kann_user_ticket_sehen(ticket, current_user, db):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Sie haben keinen Zugriff auf dieses Ticket"
        )
    
    # Aktualisiere Felder
    if ticket_update.titel is not None:
        ticket.titel = ticket_update.titel
    if ticket_update.beschreibung is not None:
        ticket.beschreibung = ticket_update.beschreibung
    if ticket_update.fälligkeitsdatum is not None:
        ticket.fälligkeitsdatum = ticket_update.fälligkeitsdatum
    if ticket_update.dringlichkeit is not None:
        ticket.dringlichkeit = ticket_update.dringlichkeit
    if ticket_update.geschlossen is not None:
        # Prüfe Berechtigung zum Schließen: Nur Admin oder Ersteller
        if ticket_update.geschlossen:
            if current_user.role != UserRole.ADMIN and ticket.erstellt_von_user_id != current_user.id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Nur Admin oder der Ersteller des Tickets können das Ticket schließen"
                )
        ticket.geschlossen = 1 if ticket_update.geschlossen else 0
    
    ticket.aktualisiert_am = datetime.utcnow()
    
    db.commit()
    db.refresh(ticket)
    
    return lade_ticket_details(ticket, db)


@router.post("/{ticket_id}/teilnehmer", response_model=TicketRead)
def fuege_teilnehmer_hinzu(
    ticket_id: int,
    teilnehmer_data: TicketTeilnehmerHinzufuegen,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Fügt Teilnehmer zu einem Ticket hinzu.
    Nur Teilnehmer können weitere Teilnehmer hinzufügen.
    """
    ticket = db.query(Ticket).filter(Ticket.id == ticket_id).first()
    
    if not ticket:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ticket nicht gefunden"
        )
    
    # Prüfe Berechtigung
    if not kann_user_ticket_sehen(ticket, current_user, db):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Sie haben keinen Zugriff auf dieses Ticket"
        )
    
    # Prüfe, dass alle Benutzer existieren
    users = db.query(User).filter(User.id.in_(teilnehmer_data.user_ids)).all()
    if len(users) != len(teilnehmer_data.user_ids):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ein oder mehrere Benutzer wurden nicht gefunden"
        )
    
    # Füge neue Teilnehmer hinzu
    vorhandene_teilnehmer_ids = {t.user_id for t in ticket.teilnehmer}
    
    for user_id in teilnehmer_data.user_ids:
        if user_id not in vorhandene_teilnehmer_ids:
            teilnehmer = TicketTeilnehmer(
                ticket_id=ticket.id,
                user_id=user_id
            )
            db.add(teilnehmer)
            
            # Füge neuen Teilnehmer zur Chat-Gruppe hinzu
            if ticket.chat_gruppe_id:
                gruppe_teilnehmer = ChatGruppeTeilnehmer(
                    chat_gruppe_id=ticket.chat_gruppe_id,
                    user_id=user_id
                )
                db.add(gruppe_teilnehmer)
                
                # Sende Nachricht in der Chat-Gruppe
                new_user = db.query(User).filter(User.id == user_id).first()
                ticket_nachricht = f"👤 **{current_user.username}** hat **{new_user.username if new_user else 'Unbekannt'}** zum Ticket hinzugefügt"
                
                chat_message = ChatMessage(
                    from_user_id=current_user.id,
                    chat_gruppe_id=ticket.chat_gruppe_id,
                    nachricht=ticket_nachricht,
                    gelesen=False
                )
                db.add(chat_message)
    
    db.commit()
    db.refresh(ticket)
    
    return lade_ticket_details(ticket, db)


def lade_ticket_details(ticket: Ticket, db: Session) -> TicketRead:
    """Lädt alle Details eines Tickets für die Response"""
    # Lade Teilnehmer-Informationen
    teilnehmer_liste = []
    for teilnehmer in ticket.teilnehmer:
        teilnehmer_liste.append({
            "id": teilnehmer.user.id,
            "username": teilnehmer.user.username,
            "email": teilnehmer.user.email
        })
    
    return TicketRead(
        id=ticket.id,
        titel=ticket.titel,
        beschreibung=ticket.beschreibung,
        fälligkeitsdatum=ticket.fälligkeitsdatum,
        dringlichkeit=ticket.dringlichkeit,
        erstellt_von_user_id=ticket.erstellt_von_user_id,
        erstellt_von_username=ticket.erstellt_von.username if ticket.erstellt_von else None,
        chat_id=ticket.chat_gruppe_id,  # Für Kompatibilität
        chat_gruppe_id=ticket.chat_gruppe_id,
        erstellt_am=ticket.erstellt_am,
        aktualisiert_am=ticket.aktualisiert_am,
        geschlossen=bool(ticket.geschlossen),
        teilnehmer_ids=[t.user_id for t in ticket.teilnehmer],
        teilnehmer=teilnehmer_liste
    )


@router.post("/{ticket_id}/schliessen", response_model=TicketRead)
def schliesse_ticket(
    ticket_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Schließt ein Ticket.
    Nur Admin oder der Ersteller des Tickets können das Ticket schließen.
    """
    ticket = db.query(Ticket).filter(Ticket.id == ticket_id).first()
    
    if not ticket:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ticket nicht gefunden"
        )
    
    # Prüfe Berechtigung: Nur Admin oder Ersteller
    if current_user.role != UserRole.ADMIN and ticket.erstellt_von_user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Nur Admin oder der Ersteller des Tickets können das Ticket schließen"
        )
    
    # Schließe Ticket
    ticket.geschlossen = 1
    ticket.aktualisiert_am = datetime.utcnow()
    
    # Sende Nachricht in der Chat-Gruppe, dass das Ticket geschlossen wurde
    if ticket.chat_gruppe_id:
        from ..models import ChatMessage
        schliess_nachricht = f"🔒 **Ticket #{ticket.id} wurde von {current_user.username} geschlossen**"
        
        chat_message = ChatMessage(
            from_user_id=current_user.id,
            chat_gruppe_id=ticket.chat_gruppe_id,
            nachricht=schliess_nachricht,
            gelesen=False
        )
        db.add(chat_message)
    
    db.commit()
    db.refresh(ticket)
    
    return lade_ticket_details(ticket, db)

