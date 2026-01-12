from sqlalchemy import Column, Integer, String, Boolean, DateTime, TypeDecorator
from sqlalchemy.sql import func
import enum
from ..database import Base


class UserRole(str, enum.Enum):
    ADMIN = "admin"
    MANAGER = "manager"
    BUCHHALTER = "buchhalter"
    TELEFONIST = "telefonist"
    UPLOADER = "uploader"


class UserRoleType(TypeDecorator):
    """
    Custom TypeDecorator für UserRole Enum, der explizit String-Werte in Enum konvertiert.
    """
    impl = String
    cache_ok = True
    
    def __init__(self, length=20):
        super().__init__(length=length)
    
    def process_bind_param(self, value, dialect):
        """Konvertiert Enum zu String beim Schreiben in die DB."""
        if value is None:
            return None
        if isinstance(value, UserRole):
            return value.value
        if isinstance(value, str):
            # Versuche String zu Enum zu konvertieren
            try:
                return UserRole(value).value
            except ValueError:
                # Fallback: wenn Wert nicht gültig, verwende Standard
                return UserRole.TELEFONIST.value
        return str(value)
    
    def process_result_value(self, value, dialect):
        """Konvertiert String zu Enum beim Lesen aus der DB."""
        if value is None:
            return UserRole.TELEFONIST
        if isinstance(value, UserRole):
            return value
        if isinstance(value, str):
            # Normalisiere den Wert (Groß-/Kleinschreibung)
            value_lower = value.lower().strip()
            # Prüfe alle möglichen Werte
            for role in UserRole:
                if role.value == value_lower:
                    return role
            # Fallback: wenn Wert nicht gefunden, verwende Standard
            # Logge Warnung für Debugging
            import warnings
            warnings.warn(f"Ungültiger Rollen-Wert '{value}', verwende Standard 'telefonist'")
            return UserRole.TELEFONIST
        # Fallback für alle anderen Typen
        return UserRole.TELEFONIST


class User(Base):
    """
    Repräsentiert einen Benutzer des Systems.
    """
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, nullable=False, index=True)
    email = Column(String, unique=True, nullable=False, index=True)
    hashed_password = Column(String, nullable=False)
    is_active = Column(Boolean, default=True)
    role = Column(UserRoleType(20), default=UserRole.TELEFONIST, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

