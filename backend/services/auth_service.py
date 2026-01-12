from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
import bcrypt
from sqlalchemy.orm import Session
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer

from ..database import get_db
from ..models.user import User, UserRole
from ..config import JWT_SECRET_KEY, ACCESS_TOKEN_EXPIRE_MINUTES, REFRESH_TOKEN_EXPIRE_DAYS

# JWT-Einstellungen
SECRET_KEY = JWT_SECRET_KEY
ALGORITHM = "HS256"

# OAuth2 Scheme
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Überprüft ein Passwort gegen einen Hash."""
    # Konvertiere String zu Bytes falls nötig
    if isinstance(hashed_password, str):
        hashed_password = hashed_password.encode('utf-8')
    if isinstance(plain_password, str):
        plain_password = plain_password.encode('utf-8')
    return bcrypt.checkpw(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Erstellt einen Passwort-Hash."""
    # Konvertiere String zu Bytes
    if isinstance(password, str):
        password = password.encode('utf-8')
    # Generiere Salt und Hash
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password, salt)
    # Konvertiere zurück zu String für Speicherung
    return hashed.decode('utf-8')


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """Erstellt ein JWT-Token."""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire, "type": "access"})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def create_refresh_token(data: dict) -> str:
    """Erstellt ein Refresh-Token mit längerer Gültigkeit."""
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire, "type": "refresh"})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def verify_refresh_token(token: str) -> Optional[str]:
    """Verifiziert ein Refresh-Token und gibt den Username zurück."""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        if payload.get("type") != "refresh":
            return None
        username: str = payload.get("sub")
        return username
    except JWTError:
        return None


def get_user_by_username(db: Session, username: str) -> Optional[User]:
    """Holt einen Benutzer anhand des Benutzernamens."""
    return db.query(User).filter(User.username == username).first()


def get_user_by_email(db: Session, email: str) -> Optional[User]:
    """Holt einen Benutzer anhand der E-Mail."""
    return db.query(User).filter(User.email == email).first()


def authenticate_user(db: Session, username: str, password: str) -> Optional[User]:
    """Authentifiziert einen Benutzer."""
    user = get_user_by_username(db, username)
    if not user:
        return None
    if not verify_password(password, user.hashed_password):
        return None
    return user


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
) -> User:
    """Holt den aktuellen authentifizierten Benutzer aus dem Token."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    user = get_user_by_username(db, username=username)
    if user is None:
        raise credentials_exception
    return user


def get_current_active_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """Holt den aktuellen aktiven Benutzer."""
    if not current_user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user


# Rollen-basierte Zugriffskontrolle
def require_role(allowed_roles: list[UserRole]):
    """Dependency-Funktion für rollen-basierte Zugriffskontrolle."""
    def role_checker(current_user: User = Depends(get_current_active_user)) -> User:
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Zugriff verweigert. Erforderliche Rolle: {', '.join([r.value for r in allowed_roles])}"
            )
        return current_user
    return role_checker


def require_admin(current_user: User = Depends(get_current_active_user)) -> User:
    """Erfordert Admin-Rolle."""
    return require_role([UserRole.ADMIN])(current_user)


def require_admin_or_manager(current_user: User = Depends(get_current_active_user)) -> User:
    """Erfordert Admin oder Manager-Rolle."""
    return require_role([UserRole.ADMIN, UserRole.MANAGER])(current_user)


def require_manager_or_telefonist(current_user: User = Depends(get_current_active_user)) -> User:
    """Erfordert Manager oder Telefonist-Rolle."""
    return require_role([UserRole.ADMIN, UserRole.MANAGER, UserRole.TELEFONIST])(current_user)


def require_buchhalter(current_user: User = Depends(get_current_active_user)) -> User:
    """Erfordert Buchhalter-Rolle."""
    return require_role([UserRole.ADMIN, UserRole.BUCHHALTER])(current_user)


def require_not_telefonist(current_user: User = Depends(get_current_active_user)) -> User:
    """Erfordert, dass der Benutzer NICHT Telefonist ist (für Abrechnungen)."""
    if current_user.role == UserRole.TELEFONIST:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Telefonisten haben keinen Zugriff auf Abrechnungen"
        )
    return current_user

