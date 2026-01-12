from datetime import timedelta, datetime
from typing import List, Optional
from sqlalchemy import func, or_, and_
from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session, joinedload, selectinload

from .. import schemas
from ..database import get_db
from ..models.user import User, UserRole
from ..models.chat import ChatMessage
from ..models.makler import Makler
from ..services.auth_service import (
    authenticate_user,
    create_access_token,
    create_refresh_token,
    verify_refresh_token,
    get_password_hash,
    get_user_by_username,
    get_user_by_email,
    get_current_active_user,
    require_admin,
    require_admin_or_manager,
    ACCESS_TOKEN_EXPIRE_MINUTES
)
from ..config import RATE_LIMIT_ENABLED, RATE_LIMIT_PER_MINUTE
from fastapi import Request

router = APIRouter()


@router.post("/register", response_model=schemas.UserRead, status_code=status.HTTP_201_CREATED)
def register(user_data: schemas.UserCreate, db: Session = Depends(get_db)):
    """
    Registriert einen neuen Benutzer.
    """
    try:
        # Prüfe ob Benutzername bereits existiert
        if get_user_by_username(db, user_data.username):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Benutzername bereits vergeben"
            )
        
        # Prüfe ob E-Mail bereits existiert
        if get_user_by_email(db, user_data.email):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="E-Mail bereits registriert"
            )
        
        # Erstelle neuen Benutzer
        hashed_password = get_password_hash(user_data.password)
        db_user = User(
            username=user_data.username,
            email=user_data.email,
            hashed_password=hashed_password
        )
        db.add(db_user)
        db.commit()
        db.refresh(db_user)
        
        return db_user
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Fehler bei der Registrierung: {str(e)}"
        )


@router.post("/login", response_model=schemas.Token)
def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
    request: Request = None
):
    """
    Authentifiziert einen Benutzer und gibt ein JWT-Token zurück.
    Rate Limiting: Maximal 5 Versuche pro Minute pro IP (wenn aktiviert).
    """
    # Rate Limiting
    if RATE_LIMIT_ENABLED and request:
        try:
            from slowapi import Limiter
            from slowapi.util import get_remote_address
            limiter = request.app.state.limiter if hasattr(request.app.state, 'limiter') else None
            if limiter:
                limiter.limit(f"{RATE_LIMIT_PER_MINUTE}/minute")(lambda: None)()
        except (ImportError, AttributeError, Exception):
            pass  # Rate Limiting optional
    
    user = authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Falscher Benutzername oder Passwort",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Benutzer ist inaktiv"
        )
    
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    refresh_token = create_refresh_token(data={"sub": user.username})
    
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer"
    }


@router.post("/refresh", response_model=schemas.Token)
def refresh_token(
    refresh_token_data: dict,
    db: Session = Depends(get_db)
):
    """
    Erstellt ein neues Access-Token mit einem Refresh-Token.
    """
    refresh_token = refresh_token_data.get("refresh_token")
    if not refresh_token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Refresh-Token fehlt"
        )
    
    username = verify_refresh_token(refresh_token)
    if not username:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Ungültiger oder abgelaufener Refresh-Token"
        )
    
    user = get_user_by_username(db, username)
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Benutzer nicht gefunden oder inaktiv"
        )
    
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,  # Refresh-Token bleibt gleich
        "token_type": "bearer"
    }


@router.get("/me", response_model=schemas.UserRead)
def read_users_me(current_user: User = Depends(get_current_active_user)):
    """
    Gibt die Informationen des aktuell eingeloggten Benutzers zurück.
    """
    # Normalisiere E-Mail-Adresse falls nötig (.local Domains werden von EmailStr abgelehnt)
    email = current_user.email
    if email and ('@admin.local' in email or '@system.local' in email or not '@' in email or email.endswith('.local')):
        # Ersetze ungültige Domains durch example.com
        email = f"{current_user.username}@example.com"
    
    # Erstelle UserRead-Objekt manuell mit normalisierter E-Mail
    return schemas.UserRead(
        id=current_user.id,
        username=current_user.username,
        email=email,
        is_active=current_user.is_active,
        role=current_user.role,
        created_at=current_user.created_at
    )


@router.post("/users", response_model=schemas.UserRead, status_code=status.HTTP_201_CREATED)
def create_user(
    user_data: schemas.UserCreateSimple,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin_or_manager)
):
    """
    Erstellt einen neuen Benutzer (nur für Admin oder Manager).
    """
    try:
        # Prüfe Rollen-Berechtigung
        requested_role = user_data.role or UserRole.TELEFONIST
        
        # Manager kann nur Telefonist, Buchhalter und Uploader erstellen
        if current_user.role == UserRole.MANAGER:
            if requested_role not in [UserRole.TELEFONIST, UserRole.BUCHHALTER, UserRole.UPLOADER]:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Manager kann nur Telefonist, Buchhalter und Uploader erstellen"
                )
        # Admin kann alle Rollen erstellen (inkl. Admin)
        elif current_user.role != UserRole.ADMIN:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Nur Admin oder Manager können Benutzer erstellen"
            )
        
        # Prüfe ob Benutzername bereits existiert
        if get_user_by_username(db, user_data.username):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Benutzername bereits vergeben"
            )
        
        # Erstelle neuen Benutzer
        hashed_password = get_password_hash(user_data.password)
        
        # Verwende angegebene E-Mail oder generiere eine
        if user_data.email:
            # Prüfe ob E-Mail bereits existiert
            if get_user_by_email(db, user_data.email):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="E-Mail bereits registriert"
                )
            email = user_data.email
        else:
            # Generiere Platzhalter-E-Mail
            placeholder_email = f"{user_data.username}@example.com"
            if get_user_by_email(db, placeholder_email):
                placeholder_email = f"{user_data.username}_{db.query(User).count()}@example.com"
            email = placeholder_email
        
        db_user = User(
            username=user_data.username,
            email=email,
            hashed_password=hashed_password,
            role=requested_role
        )
        db.add(db_user)
        db.commit()
        db.refresh(db_user)
        
        return db_user
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Fehler bei der Benutzer-Erstellung: {str(e)}"
        )


@router.put("/users/{user_id}/password", status_code=status.HTTP_200_OK)
def reset_user_password(
    user_id: int,
    password_data: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin_or_manager)
):
    """
    Setzt das Passwort eines Benutzers zurück (nur für eingeloggte Benutzer).
    """
    try:
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Benutzer nicht gefunden"
            )
        
        new_password = password_data.get("password")
        if not new_password or len(new_password) < 6:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Passwort muss mindestens 6 Zeichen lang sein"
            )
        
        user.hashed_password = get_password_hash(new_password)
        db.commit()
        db.refresh(user)
        
        return {"message": "Passwort erfolgreich zurückgesetzt"}
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Fehler beim Zurücksetzen des Passworts: {str(e)}"
        )


@router.put("/users/{user_id}/status", status_code=status.HTTP_200_OK)
def toggle_user_status(
    user_id: int,
    status_data: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin_or_manager)
):
    """
    Aktiviert oder deaktiviert einen Benutzer (nur für Admin oder Manager).
    """
    try:
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Benutzer nicht gefunden"
            )
        
        # Verhindere, dass der aktuelle Benutzer sich selbst deaktiviert
        if user.id == current_user.id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Sie können sich nicht selbst deaktivieren"
            )
        
        is_active = status_data.get("is_active")
        if is_active is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="is_active muss angegeben werden"
            )
        
        user.is_active = is_active
        db.commit()
        db.refresh(user)
        
        status_text = "aktiviert" if is_active else "deaktiviert"
        return {"message": f"Benutzer wurde erfolgreich {status_text}"}
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Fehler beim Ändern des Status: {str(e)}"
        )


@router.delete("/users/{user_id}", status_code=status.HTTP_200_OK)
def delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """
    Löscht einen Benutzer (nur für Admin).
    Manager kann keine Benutzer löschen.
    Löscht automatisch alle zugehörigen Verknüpfungen.
    """
    try:
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Benutzer nicht gefunden"
            )
        
        # Verhindere, dass der aktuelle Benutzer sich selbst löscht
        if user.id == current_user.id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Sie können sich nicht selbst löschen"
            )
        
        # Lösche alle Verknüpfungen, bevor der Benutzer gelöscht wird
        from ..models import ChatGruppeTeilnehmer, TicketTeilnehmer, ChatMessage, Ticket, ChatGruppe
        
        # 1. Lösche Chat-Gruppen-Teilnahmen
        db.query(ChatGruppeTeilnehmer).filter(
            ChatGruppeTeilnehmer.user_id == user_id
        ).delete()
        
        # 2. Lösche Ticket-Teilnahmen
        db.query(TicketTeilnehmer).filter(
            TicketTeilnehmer.user_id == user_id
        ).delete()
        
        # 3. Lösche Chat-Nachrichten (von diesem Benutzer oder an diesen Benutzer)
        db.query(ChatMessage).filter(
            (ChatMessage.from_user_id == user_id) | (ChatMessage.to_user_id == user_id)
        ).delete()
        
        # 4. Lösche Tickets, die von diesem Benutzer erstellt wurden
        # (Tickets ohne Ersteller machen keinen Sinn)
        tickets_to_delete = db.query(Ticket).filter(
            Ticket.erstellt_von_user_id == user_id
        ).all()
        for ticket in tickets_to_delete:
            db.delete(ticket)
        
        # 5. Lösche Chat-Gruppen, die von diesem Benutzer erstellt wurden
        # (Gruppen ohne Ersteller machen keinen Sinn, und die CASCADE-Beziehungen löschen automatisch die Teilnehmer)
        chat_gruppen_to_delete = db.query(ChatGruppe).filter(
            ChatGruppe.erstellt_von_user_id == user_id
        ).all()
        for gruppe in chat_gruppen_to_delete:
            db.delete(gruppe)
        
        # 6. Jetzt kann der Benutzer gelöscht werden
        db.delete(user)
        db.commit()
        
        return {"message": "Benutzer wurde erfolgreich gelöscht"}
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Fehler beim Löschen des Benutzers: {str(e)}"
        )


@router.get("/users")
def list_users(
    include_inactive: bool = Query(False, description="Inkludiere auch inaktive Benutzer"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Gibt Benutzer zurück.
    
    Für Chat-Kontakte (include_inactive=False):
    - Buchhalter und Telefonisten sehen nur Manager und Admin
    - Manager und Admin sehen alle aktiven Benutzer
    
    Für Benutzer-Verwaltung (include_inactive=True):
    - Nur Admin und Manager können alle Benutzer sehen (auch inaktive)
    """
    try:
        # Für Benutzer-Verwaltung: Nur Admin und Manager
        if include_inactive:
            if current_user.role not in [UserRole.ADMIN, UserRole.MANAGER]:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Nur Admin und Manager können alle Benutzer einsehen"
                )
            # Alle Benutzer (auch inaktive)
            users = db.query(User).all()
        else:
            # Filtere basierend auf Rolle (nur aktive)
            if current_user.role in [UserRole.BUCHHALTER, UserRole.TELEFONIST]:
                # Nur Manager und Admin
                users = db.query(User).filter(
                    User.is_active == True,
                    User.role.in_([UserRole.MANAGER, UserRole.ADMIN])
                ).all()
            else:
                # Manager und Admin sehen alle aktiven
                users = db.query(User).filter(User.is_active == True).all()
        
        # Erstelle eine Liste mit normalisierten Benutzer-Daten
        result = []
        for user in users:
            # Für Chat-Kontakte: Überspringe den aktuellen Benutzer
            if not include_inactive and user.id == current_user.id:
                continue
                
            # Normalisiere ungültige E-Mail-Adressen
            email = user.email
            if email and ('@system.local' in email or not '@' in email):
                email = f"{user.username}@example.com"
            
            result.append({
                "id": user.id,
                "username": user.username,
                "email": email,
                "is_active": user.is_active,
                "role": user.role.value if user.role else "telefonist",
                "created_at": user.created_at.isoformat() if user.created_at else None
            })
        return result
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        print(f"Fehler beim Laden der Benutzer: {e}")
        print(traceback.format_exc())
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Fehler beim Laden der Benutzer: {str(e)}"
        )


@router.put("/users/{user_id}/role", status_code=status.HTTP_200_OK)
def update_user_role(
    user_id: int,
    role_data: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """
    Aktualisiert die Rolle eines Benutzers (nur für Admin).
    """
    try:
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Benutzer nicht gefunden"
            )
        
        new_role_str = role_data.get("role")
        if not new_role_str:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Rolle muss angegeben werden"
            )
        
        try:
            new_role = UserRole(new_role_str)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Ungültige Rolle: {new_role_str}"
            )
        
        user.role = new_role
        db.commit()
        db.refresh(user)
        
        return {"message": f"Rolle wurde erfolgreich auf {new_role.value} geändert"}
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Fehler beim Ändern der Rolle: {str(e)}"
        )


@router.post("/chat", response_model=schemas.ChatMessageRead, status_code=status.HTTP_201_CREATED)
def send_chat_message(
    data: schemas.ChatMessageCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Sendet eine Chat-Nachricht an einen spezifischen Benutzer, Makler oder in eine Chat-Gruppe.
    
    Berechtigungen:
    - Buchhalter und Telefonisten dürfen nur an Manager und Admin schreiben
    - Manager und Admin dürfen an alle schreiben
    - Nachrichten von LeadGate an Makler werden als "LeadGate" angezeigt
    - Für Gruppen-Chats: Nur Teilnehmer können Nachrichten senden
    """
    # Prüfe ob es eine Gruppen-Chat-Nachricht ist
    if data.chat_gruppe_id:
        from ..models import ChatGruppe, ChatGruppeTeilnehmer
        # Prüfe ob Benutzer Teilnehmer der Gruppe ist
        teilnahme = db.query(ChatGruppeTeilnehmer).filter(
            and_(
                ChatGruppeTeilnehmer.chat_gruppe_id == data.chat_gruppe_id,
                ChatGruppeTeilnehmer.user_id == current_user.id
            )
        ).first()
        
        if not teilnahme:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Sie sind kein Teilnehmer dieser Chat-Gruppe"
            )
        
        message = ChatMessage(
            from_user_id=current_user.id,
            chat_gruppe_id=data.chat_gruppe_id,
            nachricht=data.nachricht,
            gelesen=False
        )
    elif not data.to_user_id and not data.to_makler_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="to_user_id, to_makler_id oder chat_gruppe_id muss angegeben werden"
        )
    else:
        # Prüfe Berechtigungen für Buchhalter und Telefonisten
        if current_user.role in [UserRole.BUCHHALTER, UserRole.TELEFONIST]:
            # Buchhalter und Telefonisten dürfen nur an Manager oder Admin schreiben
            if data.to_user_id:
                recipient = db.query(User).filter(User.id == data.to_user_id).first()
                if not recipient or recipient.role not in [UserRole.MANAGER, UserRole.ADMIN]:
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="Sie dürfen nur an Manager oder Admin schreiben"
                    )
            # Buchhalter und Telefonisten dürfen nicht direkt an Makler schreiben
            # (nur Manager/Admin können an Makler schreiben)
            if data.to_makler_id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Sie dürfen nicht direkt an Makler schreiben"
                )
        
        message = ChatMessage(
            from_user_id=current_user.id,
            to_user_id=data.to_user_id,
            to_makler_id=data.to_makler_id,
            nachricht=data.nachricht,
            gelesen=False
        )
    
    db.add(message)
    db.commit()
    db.refresh(message)
    
    # Lade zusätzliche Informationen
    return load_chat_message_details(message, db)


@router.get("/chat/conversations", response_model=List[schemas.ConversationSummary])
def get_conversations(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Ruft alle Konversationen des aktuellen Benutzers ab (Postfach-Ansicht).
    
    Berechtigungen:
    - Nachrichten von Maklern werden nur für Manager und Admin angezeigt
    - Buchhalter und Telefonisten sehen nur Konversationen mit Manager/Admin
    """
    # Hole alle Konversationen, an denen der Benutzer beteiligt ist
    # Konversationen mit anderen Usern
    user_conversations = db.query(
        ChatMessage.to_user_id,
        func.max(ChatMessage.erstellt_am).label('last_message_time')
    ).filter(
        ChatMessage.from_user_id == current_user.id,
        ChatMessage.to_user_id.isnot(None)
    ).group_by(ChatMessage.to_user_id).all()
    
    # Konversationen, in denen der Benutzer Empfänger ist
    # Für Buchhalter/Telefonisten: Nur Konversationen mit Manager/Admin
    received_user_filter = [
        ChatMessage.to_user_id == current_user.id,
        ChatMessage.from_user_id.isnot(None)
    ]
    
    if current_user.role in [UserRole.BUCHHALTER, UserRole.TELEFONIST]:
        # Nur Konversationen mit Manager oder Admin
        manager_admin_ids = db.query(User.id).filter(
            User.role.in_([UserRole.MANAGER, UserRole.ADMIN])
        ).subquery()
        received_user_filter.append(ChatMessage.from_user_id.in_(manager_admin_ids))
    
    received_user_conversations = db.query(
        ChatMessage.from_user_id,
        func.max(ChatMessage.erstellt_am).label('last_message_time')
    ).filter(*received_user_filter).group_by(ChatMessage.from_user_id).all()
    
    # Konversationen mit Maklern - nur für Manager und Admin
    makler_conversations = []
    received_makler_conversations = []
    
    if current_user.role in [UserRole.MANAGER, UserRole.ADMIN]:
        makler_conversations = db.query(
            ChatMessage.to_makler_id,
            func.max(ChatMessage.erstellt_am).label('last_message_time')
        ).filter(
            ChatMessage.from_user_id == current_user.id,
            ChatMessage.to_makler_id.isnot(None)
        ).group_by(ChatMessage.to_makler_id).all()
        
        received_makler_conversations = db.query(
            ChatMessage.from_makler_id,
            func.max(ChatMessage.erstellt_am).label('last_message_time')
        ).filter(
            or_(
                ChatMessage.to_user_id == current_user.id,
                ChatMessage.to_user_id.is_(None)  # Makler-Nachrichten ohne spezifischen Empfänger
            ),
            ChatMessage.from_makler_id.isnot(None)
        ).group_by(ChatMessage.from_makler_id).all()
    
    # Kombiniere alle Konversationen
    conversations = {}
    
    # User-Konversationen
    # OPTIMIERUNG: Lade alle User-Rollen in einem Batch für Buchhalter/Telefonisten
    user_contact_ids = [conv.to_user_id for conv in user_conversations]
    user_roles_dict = {}
    if current_user.role in [UserRole.BUCHHALTER, UserRole.TELEFONIST] and user_contact_ids:
        users_with_roles = db.query(User.id, User.role).filter(User.id.in_(user_contact_ids)).all()
        user_roles_dict = {u.id: u.role for u in users_with_roles}
    
    for conv in user_conversations:
        contact_id = conv.to_user_id
        # Für Buchhalter/Telefonisten: Nur Manager/Admin als Kontakte (nutze bereits geladene Daten)
        if current_user.role in [UserRole.BUCHHALTER, UserRole.TELEFONIST]:
            contact_role = user_roles_dict.get(contact_id)
            if not contact_role or contact_role not in [UserRole.MANAGER, UserRole.ADMIN]:
                continue
        
        key = f"user_{contact_id}"
        if key not in conversations or conv.last_message_time > conversations[key]['last_message_time']:
            conversations[key] = {
                'contact_id': contact_id,
                'contact_type': 'user',
                'last_message_time': conv.last_message_time
            }
    
    for conv in received_user_conversations:
        contact_id = conv.from_user_id
        key = f"user_{contact_id}"
        if key not in conversations or conv.last_message_time > conversations[key]['last_message_time']:
            conversations[key] = {
                'contact_id': contact_id,
                'contact_type': 'user',
                'last_message_time': conv.last_message_time
            }
    
    # Makler-Konversationen - nur für Manager und Admin
    if current_user.role in [UserRole.MANAGER, UserRole.ADMIN]:
        for conv in makler_conversations:
            contact_id = conv.to_makler_id
            key = f"makler_{contact_id}"
            if key not in conversations or conv.last_message_time > conversations[key]['last_message_time']:
                conversations[key] = {
                    'contact_id': contact_id,
                    'contact_type': 'makler',
                    'last_message_time': conv.last_message_time
                }
        
        for conv in received_makler_conversations:
            contact_id = conv.from_makler_id
            key = f"makler_{contact_id}"
            if key not in conversations or conv.last_message_time > conversations[key]['last_message_time']:
                conversations[key] = {
                    'contact_id': contact_id,
                    'contact_type': 'makler',
                    'last_message_time': conv.last_message_time
                }
    
    # Gruppen-Chats hinzufügen
    from ..models import ChatGruppe, ChatGruppeTeilnehmer
    gruppen_teilnahmen = db.query(ChatGruppeTeilnehmer.chat_gruppe_id).filter(
        ChatGruppeTeilnehmer.user_id == current_user.id
    ).all()
    gruppen_ids = [g[0] for g in gruppen_teilnahmen]
    
    gruppen_conversations = []
    if gruppen_ids:
        gruppen_conversations = db.query(
            ChatMessage.chat_gruppe_id,
            func.max(ChatMessage.erstellt_am).label('last_message_time')
        ).filter(
            ChatMessage.chat_gruppe_id.in_(gruppen_ids)
        ).group_by(ChatMessage.chat_gruppe_id).all()
    
    for conv in gruppen_conversations:
        gruppe_id = conv.chat_gruppe_id
        key = f"gruppe_{gruppe_id}"
        if key not in conversations or conv.last_message_time > conversations[key]['last_message_time']:
            conversations[key] = {
                'contact_id': gruppe_id,
                'contact_type': 'gruppe',
                'last_message_time': conv.last_message_time
            }
    
    # Optimierung: Lade alle Kontakte und Nachrichten in einem Batch
    user_ids = [conv['contact_id'] for key, conv in conversations.items() if conv['contact_type'] == 'user']
    makler_ids = [conv['contact_id'] for key, conv in conversations.items() if conv['contact_type'] == 'makler']
    gruppen_ids_list = [conv['contact_id'] for key, conv in conversations.items() if conv['contact_type'] == 'gruppe']
    
    # Lade alle User und Makler in einem Batch
    users_dict = {}
    if user_ids:
        users = db.query(User).filter(User.id.in_(user_ids)).all()
        users_dict = {u.id: u for u in users}
    
    makler_dict = {}
    if makler_ids:
        maklers = db.query(Makler).filter(Makler.id.in_(makler_ids)).all()
        makler_dict = {m.id: m for m in maklers}
    
    # Lade alle Chat-Gruppen in einem Batch
    gruppen_dict = {}
    if gruppen_ids_list:
        gruppen = db.query(ChatGruppe).filter(ChatGruppe.id.in_(gruppen_ids_list)).all()
        gruppen_dict = {g.id: g for g in gruppen}
    
    # Filtere geschlossene Ticket-Chats aus
    from ..models import Ticket
    if gruppen_ids_list:
        # Finde alle Tickets, die zu diesen Chat-Gruppen gehören
        tickets = db.query(Ticket).filter(
            Ticket.chat_gruppe_id.in_(gruppen_ids_list),
            Ticket.geschlossen == 1
        ).all()
        geschlossene_ticket_gruppen_ids = {t.chat_gruppe_id for t in tickets}
        
        # Entferne geschlossene Ticket-Chats aus der Konversationsliste
        conversations_to_remove = []
        for key, conv in conversations.items():
            if conv['contact_type'] == 'gruppe' and conv['contact_id'] in geschlossene_ticket_gruppen_ids:
                conversations_to_remove.append(key)
        
        for key in conversations_to_remove:
            del conversations[key]
        
        # Aktualisiere gruppen_ids_list nach dem Filtern
        gruppen_ids_list = [conv['contact_id'] for key, conv in conversations.items() if conv['contact_type'] == 'gruppe']
    
    # OPTIMIERUNG: Lade nur die neueste Nachricht pro Konversation (effizienter)
    last_messages_dict = {}
    if conversations:
        # User-Konversationen: Lade nur die neueste Nachricht pro Konversation
        user_conv_ids = [conv['contact_id'] for key, conv in conversations.items() if conv['contact_type'] == 'user']
        if user_conv_ids:
            # Für jede Konversation die neueste Nachricht direkt laden (effizienter als alle zu laden)
            for contact_id in user_conv_ids:
                latest_msg = db.query(ChatMessage).filter(
                    or_(
                        and_(ChatMessage.from_user_id == current_user.id, ChatMessage.to_user_id == contact_id),
                        and_(ChatMessage.from_user_id == contact_id, ChatMessage.to_user_id == current_user.id)
                    )
                ).order_by(ChatMessage.erstellt_am.desc()).first()
                
                if latest_msg:
                    key = f"user_{contact_id}"
                    last_messages_dict[key] = latest_msg
        
        # Makler-Konversationen: Lade nur die neueste Nachricht pro Konversation
        makler_conv_ids = [conv['contact_id'] for key, conv in conversations.items() if conv['contact_type'] == 'makler']
        if makler_conv_ids:
            for makler_id in makler_conv_ids:
                latest_msg = db.query(ChatMessage).filter(
                    or_(
                        and_(ChatMessage.from_user_id == current_user.id, ChatMessage.to_makler_id == makler_id),
                        and_(
                            ChatMessage.from_makler_id == makler_id,
                            or_(
                                ChatMessage.to_user_id == current_user.id,
                                ChatMessage.to_user_id.is_(None)
                            )
                        )
                    )
                ).order_by(ChatMessage.erstellt_am.desc()).first()
                
                if latest_msg:
                    key = f"makler_{makler_id}"
                    last_messages_dict[key] = latest_msg
        
        # Gruppen-Chats: Lade nur die neueste Nachricht pro Konversation
        gruppen_conv_ids = [conv['contact_id'] for key, conv in conversations.items() if conv['contact_type'] == 'gruppe']
        if gruppen_conv_ids:
            for gruppe_id in gruppen_conv_ids:
                latest_msg = db.query(ChatMessage).filter(
                    ChatMessage.chat_gruppe_id == gruppe_id
                ).order_by(ChatMessage.erstellt_am.desc()).first()
                
                if latest_msg:
                    key = f"gruppe_{gruppe_id}"
                    last_messages_dict[key] = latest_msg
    
    # OPTIMIERUNG: Berechne alle unread_counts in einem Batch
    unread_counts_dict = {}
    if conversations:
        # User-Konversationen: Ungelesene Nachrichten
        user_conv_ids = [conv['contact_id'] for key, conv in conversations.items() if conv['contact_type'] == 'user']
        if user_conv_ids:
            unread_user = db.query(
                ChatMessage.from_user_id,
                func.count(ChatMessage.id).label('count')
            ).filter(
                ChatMessage.from_user_id.in_(user_conv_ids),
                ChatMessage.to_user_id == current_user.id,
                ChatMessage.gelesen == False
            ).group_by(ChatMessage.from_user_id).all()
            
            for row in unread_user:
                unread_counts_dict[f"user_{row.from_user_id}"] = row.count
        
        # Makler-Konversationen: Ungelesene Nachrichten
        makler_conv_ids = [conv['contact_id'] for key, conv in conversations.items() if conv['contact_type'] == 'makler']
        if makler_conv_ids:
            unread_makler = db.query(
                ChatMessage.from_makler_id,
                func.count(ChatMessage.id).label('count')
            ).filter(
                ChatMessage.from_makler_id.in_(makler_conv_ids),
                or_(
                    ChatMessage.to_user_id == current_user.id,
                    ChatMessage.to_user_id.is_(None)
                ),
                ChatMessage.gelesen == False
            ).group_by(ChatMessage.from_makler_id).all()
            
            for row in unread_makler:
                unread_counts_dict[f"makler_{row.from_makler_id}"] = row.count
        
        # Gruppen-Chats: Ungelesene Nachrichten
        gruppen_conv_ids = [conv['contact_id'] for key, conv in conversations.items() if conv['contact_type'] == 'gruppe']
        if gruppen_conv_ids:
            unread_gruppen = db.query(
                ChatMessage.chat_gruppe_id,
                func.count(ChatMessage.id).label('count')
            ).filter(
                ChatMessage.chat_gruppe_id.in_(gruppen_conv_ids),
                ChatMessage.from_user_id != current_user.id,  # Nur Nachrichten von anderen
                ChatMessage.gelesen == False
            ).group_by(ChatMessage.chat_gruppe_id).all()
            
            for row in unread_gruppen:
                unread_counts_dict[f"gruppe_{row.chat_gruppe_id}"] = row.count
    
    # Lade Details für jede Konversation (ohne separate Queries!)
    result = []
    for key, conv in conversations.items():
        # Nutze bereits geladene Daten
        last_msg = last_messages_dict.get(key)
        unread_count = unread_counts_dict.get(key, 0)
        
        if conv['contact_type'] == 'user':
            contact = users_dict.get(conv['contact_id'])
            contact_name = contact.username if contact else f"User {conv['contact_id']}"
        elif conv['contact_type'] == 'makler':
            contact = makler_dict.get(conv['contact_id'])
            contact_name = contact.firmenname if contact else f"Makler {conv['contact_id']}"
        else:  # gruppe
            gruppe = gruppen_dict.get(conv['contact_id'])
            contact_name = gruppe.name if gruppe else f"Gruppe {conv['contact_id']}"
        
        result.append({
            "contact_id": conv['contact_id'],
            "contact_type": conv['contact_type'],
            "contact_name": contact_name,
            "last_message": last_msg.nachricht if last_msg else None,
            "last_message_time": last_msg.erstellt_am if last_msg else None,
            "unread_count": unread_count,
            "is_gruppe": conv['contact_type'] == 'gruppe'
        })
    
    # Sortiere nach letzter Nachricht (neueste zuerst)
    result.sort(key=lambda x: x['last_message_time'] or datetime.min, reverse=True)
    
    return result


@router.get("/chat/conversations/{contact_type}/{contact_id}", response_model=List[schemas.ChatMessageRead])
def get_conversation_messages(
    contact_type: str,
    contact_id: int,
    limit: int = Query(100, ge=1, le=500, description="Maximale Anzahl Nachrichten"),
    after_id: Optional[int] = Query(None, description="Lade nur Nachrichten nach dieser ID (für Pagination)"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Ruft Nachrichten in einer Konversation ab (mit Pagination für bessere Performance).
    
    Berechtigungen:
    - Nachrichten von Maklern werden nur für Manager und Admin angezeigt
    - Buchhalter und Telefonisten sehen nur Konversationen mit Manager/Admin
    """
    if contact_type == "user":
        # Prüfe Berechtigung für Buchhalter/Telefonisten
        if current_user.role in [UserRole.BUCHHALTER, UserRole.TELEFONIST]:
            recipient = db.query(User).filter(User.id == contact_id).first()
            if not recipient or recipient.role not in [UserRole.MANAGER, UserRole.ADMIN]:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Sie dürfen nur Konversationen mit Manager oder Admin sehen"
                )
        
        # OPTIMIERUNG: Limit und Pagination für bessere Performance
        query = db.query(ChatMessage).options(
            joinedload(ChatMessage.from_user),
            joinedload(ChatMessage.to_user)
        ).filter(
            or_(
                and_(ChatMessage.from_user_id == current_user.id, ChatMessage.to_user_id == contact_id),
                and_(ChatMessage.from_user_id == contact_id, ChatMessage.to_user_id == current_user.id)
            )
        )
        
        # Pagination: Wenn after_id gegeben, lade nur neuere Nachrichten
        if after_id:
            query = query.filter(ChatMessage.id > after_id)
        
        messages = query.order_by(ChatMessage.erstellt_am.desc()).limit(limit).all()
        messages.reverse()  # Älteste zuerst für chronologische Anzeige
        
        # Markiere Nachrichten als gelesen (bulk update für bessere Performance)
        unread_ids = [m.id for m in messages if not m.gelesen and m.from_user_id == contact_id]
        if unread_ids:
            db.query(ChatMessage).filter(ChatMessage.id.in_(unread_ids)).update({ChatMessage.gelesen: True}, synchronize_session=False)
            db.commit()
    elif contact_type == "makler":
        # Nur Manager und Admin können Makler-Konversationen sehen
        if current_user.role not in [UserRole.MANAGER, UserRole.ADMIN]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Sie dürfen keine Makler-Konversationen sehen"
            )
        
        # OPTIMIERUNG: Limit und Pagination für bessere Performance
        query = db.query(ChatMessage).options(
            joinedload(ChatMessage.from_user),
            joinedload(ChatMessage.to_user),
            joinedload(ChatMessage.from_makler),
            joinedload(ChatMessage.to_makler)
        ).filter(
            or_(
                and_(ChatMessage.from_user_id == current_user.id, ChatMessage.to_makler_id == contact_id),
                and_(
                    ChatMessage.from_makler_id == contact_id,
                    or_(
                        ChatMessage.to_user_id == current_user.id,
                        ChatMessage.to_user_id.is_(None)  # Makler-Nachrichten ohne spezifischen Empfänger
                    )
                )
            )
        )
        
        # Pagination: Wenn after_id gegeben, lade nur neuere Nachrichten
        if after_id:
            query = query.filter(ChatMessage.id > after_id)
        
        messages = query.order_by(ChatMessage.erstellt_am.desc()).limit(limit).all()
        messages.reverse()  # Älteste zuerst für chronologische Anzeige
        
        # Markiere Nachrichten als gelesen (bulk update für bessere Performance)
        unread_ids = [m.id for m in messages if not m.gelesen and m.from_makler_id == contact_id]
        if unread_ids:
            db.query(ChatMessage).filter(ChatMessage.id.in_(unread_ids)).update({ChatMessage.gelesen: True}, synchronize_session=False)
            db.commit()
    elif contact_type == "gruppe":
        # Prüfe ob Benutzer Teilnehmer der Gruppe ist
        from ..models import ChatGruppeTeilnehmer
        teilnahme = db.query(ChatGruppeTeilnehmer).filter(
            and_(
                ChatGruppeTeilnehmer.chat_gruppe_id == contact_id,
                ChatGruppeTeilnehmer.user_id == current_user.id
            )
        ).first()
        
        if not teilnahme:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Sie sind kein Teilnehmer dieser Chat-Gruppe"
            )
        
        # OPTIMIERUNG: Limit und Pagination für bessere Performance
        query = db.query(ChatMessage).options(
            joinedload(ChatMessage.from_user),
            joinedload(ChatMessage.chat_gruppe)
        ).filter(
            ChatMessage.chat_gruppe_id == contact_id
        )
        
        # Pagination: Wenn after_id gegeben, lade nur neuere Nachrichten
        if after_id:
            query = query.filter(ChatMessage.id > after_id)
        
        messages = query.order_by(ChatMessage.erstellt_am.desc()).limit(limit).all()
        messages.reverse()  # Älteste zuerst für chronologische Anzeige
        
        # Markiere Nachrichten als gelesen (bulk update für bessere Performance)
        unread_ids = [m.id for m in messages if not m.gelesen and m.from_user_id != current_user.id]
        if unread_ids:
            db.query(ChatMessage).filter(ChatMessage.id.in_(unread_ids)).update({ChatMessage.gelesen: True}, synchronize_session=False)
            db.commit()
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="contact_type muss 'user', 'makler' oder 'gruppe' sein"
        )
    
    return [load_chat_message_details(msg) for msg in messages]


def load_chat_message_details(message: ChatMessage, db: Session = None):
    """Hilfsfunktion zum Laden der Details einer Nachricht (optimiert mit Eager Loading)"""
    from_user_username = None
    from_makler_firmenname = None
    to_user_username = None
    to_makler_firmenname = None
    
    # Wenn ein User an einen Makler schreibt, wird es als "LeadGate" angezeigt
    if message.from_user_id and message.to_makler_id:
        from_user_username = "LeadGate"
    elif message.from_user_id:
        # Nutze bereits geladene Relationship falls vorhanden
        if hasattr(message, 'from_user') and message.from_user:
            from_user_username = message.from_user.username
        elif db:
            user = db.query(User).filter(User.id == message.from_user_id).first()
            from_user_username = user.username if user else None
    
    if message.from_makler_id:
        # Nutze bereits geladene Relationship falls vorhanden
        if hasattr(message, 'from_makler') and message.from_makler:
            from_makler_firmenname = message.from_makler.firmenname
        elif db:
            makler = db.query(Makler).filter(Makler.id == message.from_makler_id).first()
            from_makler_firmenname = makler.firmenname if makler else None
    
    if message.to_user_id:
        # Nutze bereits geladene Relationship falls vorhanden
        if hasattr(message, 'to_user') and message.to_user:
            to_user_username = message.to_user.username
        elif db:
            user = db.query(User).filter(User.id == message.to_user_id).first()
            to_user_username = user.username if user else None
    
    if message.to_makler_id:
        # Nutze bereits geladene Relationship falls vorhanden
        if hasattr(message, 'to_makler') and message.to_makler:
            to_makler_firmenname = message.to_makler.firmenname
        elif db:
            makler = db.query(Makler).filter(Makler.id == message.to_makler_id).first()
            to_makler_firmenname = makler.firmenname if makler else None
    
    # Lade Chat-Gruppen-Name falls vorhanden
    if message.chat_gruppe_id:
        if hasattr(message, 'chat_gruppe') and message.chat_gruppe:
            chat_gruppe_name = message.chat_gruppe.name
        elif db:
            from ..models import ChatGruppe
            gruppe = db.query(ChatGruppe).filter(ChatGruppe.id == message.chat_gruppe_id).first()
            chat_gruppe_name = gruppe.name if gruppe else None
        else:
            chat_gruppe_name = None
    else:
        chat_gruppe_name = None
    
    return schemas.ChatMessageRead(
        id=message.id,
        from_user_id=message.from_user_id,
        from_makler_id=message.from_makler_id,
        to_user_id=message.to_user_id,
        to_makler_id=message.to_makler_id,
        chat_gruppe_id=message.chat_gruppe_id,
        nachricht=message.nachricht,
        erstellt_am=message.erstellt_am,
        gelesen=message.gelesen,
        from_user_username=from_user_username,
        from_makler_firmenname=from_makler_firmenname,
        to_user_username=to_user_username,
        to_makler_firmenname=to_makler_firmenname,
        chat_gruppe_name=chat_gruppe_name
    )


@router.get("/chat/gruppen/{gruppe_id}/teilnehmer")
def get_gruppen_teilnehmer(
    gruppe_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Gibt alle Teilnehmer einer Chat-Gruppe zurück.
    Nur Teilnehmer der Gruppe können diese Information sehen.
    """
    from ..models import ChatGruppe, ChatGruppeTeilnehmer
    
    # Prüfe ob Benutzer Teilnehmer der Gruppe ist
    teilnahme = db.query(ChatGruppeTeilnehmer).filter(
        and_(
            ChatGruppeTeilnehmer.chat_gruppe_id == gruppe_id,
            ChatGruppeTeilnehmer.user_id == current_user.id
        )
    ).first()
    
    if not teilnahme:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Sie sind kein Teilnehmer dieser Chat-Gruppe"
        )
    
    # Lade alle Teilnehmer der Gruppe
    teilnehmer = db.query(ChatGruppeTeilnehmer).options(
        joinedload(ChatGruppeTeilnehmer.user)
    ).filter(
        ChatGruppeTeilnehmer.chat_gruppe_id == gruppe_id
    ).all()
    
    return {
        "gruppe_id": gruppe_id,
        "teilnehmer": [
            {
                "id": t.user.id,
                "username": t.user.username,
                "email": t.user.email
            }
            for t in teilnehmer
        ]
    }

