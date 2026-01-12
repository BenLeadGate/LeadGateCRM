from fastapi import APIRouter, Depends, HTTPException, status, Request, Header
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from typing import Optional
import json

from .. import schemas
from ..database import get_db
from ..models import Makler, User
from ..services.auth_service import get_current_active_user
from ..services.stripe_service import create_payment_intent, verify_webhook_signature, handle_payment_success
from ..config import STRIPE_ENABLED, STRIPE_PUBLISHABLE_KEY

router = APIRouter()


@router.post("/makler/{makler_id}/credits/stripe/create-payment-intent")
def create_stripe_payment_intent(
    makler_id: int,
    data: schemas.MaklerCreditsAufladen,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Erstellt einen Stripe Payment Intent für eine Credits-Aufladung.
    WICHTIG: data.betrag ist der Nettobetrag (wird als Credits gutgeschrieben).
    Der Bruttobetrag (inkl. 19% MwSt) wird vom Makler bezahlt.
    Gibt client_secret zurück, das im Frontend für Stripe Elements verwendet wird.
    """
    if not STRIPE_ENABLED:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Stripe ist nicht konfiguriert"
        )
    
    makler = db.query(Makler).filter(Makler.id == makler_id).first()
    if not makler:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Makler nicht gefunden"
        )
    
    if data.betrag <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Betrag muss größer als 0 sein"
        )
    
    # Erstelle Payment Intent (betrag ist Nettobetrag, MwSt wird automatisch hinzugefügt)
    payment_intent = create_payment_intent(
        makler=makler,
        betrag_netto=data.betrag,  # Nettobetrag (wird als Credits gutgeschrieben)
        beschreibung=data.beschreibung or f"Credits-Aufladung für {makler.firmenname}"
    )
    
    return {
        "client_secret": payment_intent["client_secret"],
        "payment_intent_id": payment_intent["payment_intent_id"],
        "publishable_key": STRIPE_PUBLISHABLE_KEY,
        "amount": payment_intent["amount"],
        "currency": payment_intent["currency"],
        "betrag_netto": payment_intent["betrag_netto"],
        "betrag_brutto": payment_intent["betrag_brutto"],
        "mwst": payment_intent["mwst"]
    }


@router.post("/stripe/webhook")
async def stripe_webhook(
    request: Request,
    stripe_signature: Optional[str] = Header(None, alias="stripe-signature"),
    db: Session = Depends(get_db)
):
    """
    Webhook-Endpunkt für Stripe-Events.
    Verarbeitet erfolgreiche Zahlungen und erstellt Credits-Transaktionen.
    
    WICHTIG: 
    - Dieser Endpunkt benötigt KEINE Authentifizierung (Stripe sendet direkt)
    - Muss über HTTPS erreichbar sein in Produktion
    - Stripe-Signatur wird verifiziert für Sicherheit
    """
    """
    Webhook-Endpunkt für Stripe-Events.
    Verarbeitet erfolgreiche Zahlungen und erstellt Credits-Transaktionen.
    
    WICHTIG: Dieser Endpunkt sollte in Produktion über HTTPS erreichbar sein
    und die Stripe-Signatur muss verifiziert werden.
    """
    if not STRIPE_ENABLED:
        return JSONResponse(
            status_code=503,
            content={"error": "Stripe ist nicht konfiguriert"}
        )
    
    # Lese Request Body
    payload = await request.body()
    
    if not stripe_signature:
        return JSONResponse(
            status_code=400,
            content={"error": "Stripe-Signatur fehlt"}
        )
    
    # Verifiziere Webhook-Signatur
    event = verify_webhook_signature(payload, stripe_signature)
    
    if not event:
        return JSONResponse(
            status_code=400,
            content={"error": "Ungültige Stripe-Signatur"}
        )
    
    # Verarbeite verschiedene Event-Typen
    event_type = event.get("type")
    event_data = event.get("data", {}).get("object", {})
    
    if event_type == "payment_intent.succeeded":
        # Zahlung erfolgreich
        payment_intent_id = event_data.get("id")
        metadata = event_data.get("metadata", {})
        makler_id = metadata.get("makler_id")
        betrag_euro = metadata.get("betrag_euro")
        
        if makler_id and betrag_euro:
            try:
                makler_id_int = int(makler_id)
                betrag_float = float(betrag_euro)
                
                handle_payment_success(
                    db=db,
                    payment_intent_id=payment_intent_id,
                    makler_id=makler_id_int,
                    betrag=betrag_float
                )
                
                return JSONResponse(
                    status_code=200,
                    content={"status": "success", "message": "Credits erfolgreich aufgeladen"}
                )
            except (ValueError, TypeError) as e:
                return JSONResponse(
                    status_code=400,
                    content={"error": f"Ungültige Metadaten: {str(e)}"}
                )
    
    elif event_type == "payment_intent.payment_failed":
        # Zahlung fehlgeschlagen - könnte hier geloggt werden
        payment_intent_id = event_data.get("id")
        # Optional: Transaktion mit Status "failed" erstellen
        pass
    
    # Für andere Event-Typen einfach 200 zurückgeben
    return JSONResponse(
        status_code=200,
        content={"status": "received", "event_type": event_type}
    )


@router.get("/stripe/config")
def get_stripe_config():
    """
    Gibt die Stripe-Konfiguration zurück (nur publishable_key für Frontend).
    """
    if not STRIPE_ENABLED:
        return {
            "enabled": False,
            "publishable_key": None
        }
    
    return {
        "enabled": True,
        "publishable_key": STRIPE_PUBLISHABLE_KEY
    }

