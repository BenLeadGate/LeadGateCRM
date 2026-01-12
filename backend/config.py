import os
from typing import Optional

# Versuche python-dotenv zu laden (optional)
try:
    from dotenv import load_dotenv
    load_dotenv()  # Lädt .env Datei falls vorhanden
except ImportError:
    pass  # python-dotenv nicht installiert, verwende nur Umgebungsvariablen

# Stripe-Konfiguration
# In Produktion sollten diese Werte aus Umgebungsvariablen geladen werden
STRIPE_SECRET_KEY: Optional[str] = os.getenv("STRIPE_SECRET_KEY", None)
STRIPE_PUBLISHABLE_KEY: Optional[str] = os.getenv("STRIPE_PUBLISHABLE_KEY", None)
STRIPE_WEBHOOK_SECRET: Optional[str] = os.getenv("STRIPE_WEBHOOK_SECRET", None)

# Stripe aktiviert?
STRIPE_ENABLED: bool = STRIPE_SECRET_KEY is not None and STRIPE_PUBLISHABLE_KEY is not None

# Frontend-URL für Redirects nach Zahlung
FRONTEND_URL: str = os.getenv("FRONTEND_URL", "http://localhost:8000")

# JWT-Konfiguration
JWT_SECRET_KEY: str = os.getenv("JWT_SECRET_KEY", "your-secret-key-change-this-in-production")
if JWT_SECRET_KEY == "your-secret-key-change-this-in-production":
    import warnings
    warnings.warn("⚠️ WARNUNG: Verwende Standard-JWT-Secret-Key! In Produktion JWT_SECRET_KEY Umgebungsvariable setzen!")

# CORS-Konfiguration
ALLOWED_ORIGINS: list[str] = os.getenv("ALLOWED_ORIGINS", "http://localhost:8004,http://127.0.0.1:8004").split(",")
ALLOWED_ORIGINS = [origin.strip() for origin in ALLOWED_ORIGINS]

# Token-Ablaufzeit (24 Stunden statt 30 Tage)
ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "1440"))  # 24 Stunden
REFRESH_TOKEN_EXPIRE_DAYS: int = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "30"))  # 30 Tage

# Rate Limiting
RATE_LIMIT_ENABLED: bool = os.getenv("RATE_LIMIT_ENABLED", "true").lower() == "true"
RATE_LIMIT_PER_MINUTE: int = int(os.getenv("RATE_LIMIT_PER_MINUTE", "5"))  # 5 Login-Versuche pro Minute

# Environment
ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")

# Logging-Level
LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO" if ENVIRONMENT == "production" else "DEBUG")

