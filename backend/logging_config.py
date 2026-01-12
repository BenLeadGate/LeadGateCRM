"""
Logging-Konfiguration für LeadGate CRM
"""
import logging
import sys
from pathlib import Path
from .config import ENVIRONMENT

# Erstelle logs-Verzeichnis falls nicht vorhanden
logs_dir = Path(__file__).parent.parent / "logs"
logs_dir.mkdir(exist_ok=True)

# Logging-Konfiguration
logging.basicConfig(
    level=logging.DEBUG if ENVIRONMENT != "production" else logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(logs_dir / "leadgate.log", encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)

# Erstelle Logger für verschiedene Module
def get_logger(name: str) -> logging.Logger:
    """Erstellt einen Logger für ein Modul."""
    return logging.getLogger(f"leadgate.{name}")






