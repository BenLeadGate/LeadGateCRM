from typing import Optional, Dict, Any
import stripe
from fastapi import HTTPException, status

from ..config import STRIPE_SECRET_KEY, STRIPE_ENABLED
from ..models import Makler, MaklerCredits
from sqlalchemy.orm import Session

if STRIPE_ENABLED and STRIPE_SECRET_KEY:
    stripe.api_key = STRIPE_SECRET_KEY


def create_payment_intent(
    makler: Makler,
    betrag_netto: float,
    beschreibung: Optional[str] = None,
    metadata: Optional[Dict[str, str]] = None
) -> Dict[str, Any]:
    """
    Erstellt einen Stripe Payment Intent für eine Credits-Aufladung.
    WICHTIG: betrag_netto ist der Nettobetrag (ohne MwSt), der als Credits gutgeschrieben wird.
    Der Bruttobetrag (inkl. 19% MwSt) wird vom Makler bezahlt.
    
    Args:
        makler: Der Makler
        betrag_netto: Nettobetrag in Euro (wird als Credits gutgeschrieben)
        beschreibung: Beschreibung der Zahlung
        metadata: Zusätzliche Metadaten
    
    Returns:
        Payment Intent Objekt von Stripe mit Bruttobetrag (inkl. MwSt)
    """
    if not STRIPE_ENABLED:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Stripe ist nicht konfiguriert. Bitte STRIPE_SECRET_KEY und STRIPE_PUBLISHABLE_KEY setzen."
        )
    
    if betrag_netto <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Betrag muss größer als 0 sein"
        )
    
    # Berechne Bruttobetrag (inkl. 19% MwSt + 30 Cent Transaktionsgebühr)
    betrag_brutto = berechne_bruttobetrag(betrag_netto, 0.19, 0.30)
    mwst_betrag = berechne_mwst(betrag_netto, 0.19)
    transaktionsgebuehr = 0.30  # 30 Cent pro Transaktion
    
    # Konvertiere Bruttobetrag zu Cent (Stripe arbeitet mit Cent)
    betrag_cent = int(betrag_brutto * 100)
    
    # Erstelle Payment Intent
    try:
        payment_intent = stripe.PaymentIntent.create(
            amount=betrag_cent,
            currency="eur",
            description=beschreibung or f"Credits-Aufladung für {makler.firmenname}",
            metadata={
                "makler_id": str(makler.id),
                "makler_firmenname": makler.firmenname,
                "betrag_netto_euro": str(betrag_netto),  # Nettobetrag (wird als Credits gutgeschrieben)
                "betrag_brutto_euro": str(betrag_brutto),  # Bruttobetrag (wird bezahlt)
                "mwst_euro": str(mwst_betrag),  # MwSt-Betrag
                "transaktionsgebuehr_euro": str(transaktionsgebuehr),  # 30 Cent Transaktionsgebühr
                **(metadata or {})
            },
            automatic_payment_methods={
                "enabled": True,
            },
        )
        
        return {
            "client_secret": payment_intent.client_secret,
            "payment_intent_id": payment_intent.id,
            "amount": payment_intent.amount,
            "currency": payment_intent.currency,
            "status": payment_intent.status,
            "betrag_netto": betrag_netto,  # Für Frontend-Anzeige
            "betrag_brutto": betrag_brutto,  # Für Frontend-Anzeige
            "mwst": mwst_betrag,  # Für Frontend-Anzeige
            "transaktionsgebuehr": transaktionsgebuehr  # Für Frontend-Anzeige
        }
    except stripe.error.StripeError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Stripe-Fehler: {str(e)}"
        )


def verify_webhook_signature(payload: bytes, signature: str) -> Optional[Dict[str, Any]]:
    """
    Verifiziert die Signatur eines Stripe Webhooks.
    
    Args:
        payload: Raw request body als Bytes
        signature: Stripe-Signatur aus Header
    
    Returns:
        Event-Daten oder None bei ungültiger Signatur
    """
    from ..config import STRIPE_WEBHOOK_SECRET
    
    if not STRIPE_ENABLED or not STRIPE_WEBHOOK_SECRET:
        return None
    
    try:
        event = stripe.Webhook.construct_event(
            payload, signature, STRIPE_WEBHOOK_SECRET
        )
        return event
    except ValueError:
        # Invalid payload
        return None
    except stripe.error.SignatureVerificationError:
        # Invalid signature
        return None


def handle_payment_success(
    db: Session,
    payment_intent_id: str,
    makler_id: int,
    betrag_netto: float
) -> MaklerCredits:
    """
    Verarbeitet eine erfolgreiche Zahlung und erstellt eine Credits-Transaktion.
    WICHTIG: Nur der Nettobetrag (ohne MwSt) wird als Credits gutgeschrieben.
    
    Args:
        db: Datenbank-Session
        payment_intent_id: Stripe Payment Intent ID
        makler_id: ID des Maklers
        betrag_netto: Nettobetrag in Euro (wird als Credits gutgeschrieben)
    
    Returns:
        Erstellte MaklerCredits-Transaktion
    """
    # Prüfe ob Makler existiert
    makler = db.query(Makler).filter(Makler.id == makler_id).first()
    if not makler:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Makler nicht gefunden"
        )
    
    # Prüfe ob bereits eine Transaktion für diesen Payment Intent existiert
    existing = (
        db.query(MaklerCredits)
        .filter(MaklerCredits.zahlungsreferenz == payment_intent_id)
        .first()
    )
    
    if existing:
        # Transaktion existiert bereits (idempotent)
        return existing
    
    # Berechne MwSt und Transaktionsgebühr für Beschreibung
    mwst_betrag = berechne_mwst(betrag_netto, 0.19)
    transaktionsgebuehr = 0.30
    betrag_brutto = berechne_bruttobetrag(betrag_netto, 0.19, transaktionsgebuehr)
    
    # Erstelle Credits-Transaktion (nur Nettobetrag wird gutgeschrieben)
    transaktion = MaklerCredits(
        makler_id=makler_id,
        betrag=betrag_netto,  # Nur Nettobetrag als Credits
        transaktionstyp="zahlung_online",
        beschreibung=f"Online-Zahlung über Stripe - Netto: {betrag_netto:.2f}€, Brutto: {betrag_brutto:.2f}€ (inkl. {mwst_betrag:.2f}€ MwSt + {transaktionsgebuehr:.2f}€ Transaktionsgebühr)",
        zahlungsreferenz=payment_intent_id,
        zahlungsstatus="completed"
    )
    
    db.add(transaktion)
    db.commit()
    db.refresh(transaktion)
    
    return transaktion


def berechne_stripe_gebuehren(betrag: float) -> float:
    """
    Berechnet die Stripe-Gebühren für einen Betrag.
    Stripe-Gebühren: 2.9% + 30 Cent pro Transaktion.
    
    Args:
        betrag: Betrag in Euro
    
    Returns:
        Gebühren in Euro
    """
    return (betrag * 0.029) + 0.30


def berechne_rueckzahlungsbetrag_abzueglich_gebuehren(betrag: float) -> float:
    """
    Berechnet den Rückzahlungsbetrag abzüglich Stripe-Gebühren.
    
    Args:
        betrag: Ursprünglicher Betrag in Euro
    
    Returns:
        Rückzahlungsbetrag nach Abzug der Gebühren
    """
    gebuehren = berechne_stripe_gebuehren(betrag)
    rueckzahlungsbetrag = betrag - gebuehren
    return max(0.0, rueckzahlungsbetrag)  # Mindestens 0€


def berechne_mwst(betrag_netto: float, mwst_satz: float = 0.19) -> float:
    """
    Berechnet die Mehrwertsteuer (MwSt) für einen Nettobetrag.
    
    Args:
        betrag_netto: Nettobetrag in Euro
        mwst_satz: MwSt-Satz (Standard: 0.19 = 19%)
    
    Returns:
        MwSt-Betrag in Euro
    """
    return betrag_netto * mwst_satz


def berechne_bruttobetrag(betrag_netto: float, mwst_satz: float = 0.19, transaktionsgebuehr: float = 0.30) -> float:
    """
    Berechnet den Bruttobetrag (inkl. MwSt + 30 Cent Transaktionsgebühr) für einen Nettobetrag.
    
    Args:
        betrag_netto: Nettobetrag in Euro (wird als Credits gutgeschrieben)
        mwst_satz: MwSt-Satz (Standard: 0.19 = 19%)
        transaktionsgebuehr: Transaktionsgebühr in Euro (Standard: 0.30 = 30 Cent)
    
    Returns:
        Bruttobetrag in Euro (inkl. MwSt + Transaktionsgebühr)
    """
    mwst = betrag_netto * mwst_satz
    return betrag_netto + mwst + transaktionsgebuehr


def berechne_nettobetrag(betrag_brutto: float, mwst_satz: float = 0.19) -> float:
    """
    Berechnet den Nettobetrag aus einem Bruttobetrag.
    
    Args:
        betrag_brutto: Bruttobetrag in Euro (inkl. MwSt)
        mwst_satz: MwSt-Satz (Standard: 0.19 = 19%)
    
    Returns:
        Nettobetrag in Euro
    """
    return betrag_brutto / (1 + mwst_satz)


def create_refund(
    payment_intent_id: str,
    betrag: float,
    beschreibung: Optional[str] = None
) -> Dict[str, Any]:
    """
    Erstellt eine Rückerstattung (Refund) über Stripe.
    WICHTIG: Der Betrag wird bereits um Stripe-Gebühren reduziert sein.
    
    Args:
        payment_intent_id: Stripe Payment Intent ID der ursprünglichen Zahlung
        betrag: Betrag in Euro, der zurückerstattet werden soll (bereits abzüglich Gebühren)
        beschreibung: Optionale Beschreibung für die Rückerstattung
    
    Returns:
        Stripe Refund Objekt
    """
    if not STRIPE_ENABLED:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Stripe ist nicht konfiguriert"
        )
    
    if betrag <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Betrag muss größer als 0 sein"
        )
    
    # Konvertiere Euro zu Cent
    betrag_cent = int(betrag * 100)
    
    try:
        # Hole Payment Intent
        payment_intent = stripe.PaymentIntent.retrieve(payment_intent_id)
        
        # Prüfe ob bereits eine Rückerstattung existiert
        refunds = stripe.Refund.list(payment_intent=payment_intent_id)
        bereits_zurueckgezahlt = sum(r.amount for r in refunds.data)
        
        if bereits_zurueckgezahlt >= payment_intent.amount:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Diese Zahlung wurde bereits vollständig zurückerstattet"
            )
        
        # Erstelle Refund
        refund = stripe.Refund.create(
            payment_intent=payment_intent_id,
            amount=betrag_cent,
            reason="requested_by_customer",
            metadata={
                "description": beschreibung or f"Rückerstattung für Credits: {betrag:.2f}€"
            }
        )
        
        return {
            "id": refund.id,
            "amount": refund.amount / 100,  # Cent zu Euro
            "status": refund.status,
            "currency": refund.currency
        }
    
    except stripe.error.InvalidRequestError as e:
        # Spezifische Fehlerbehandlung für verschiedene Stripe-Fehler
        error_message = str(e)
        if "insufficient" in error_message.lower() or "balance" in error_message.lower():
            raise HTTPException(
                status_code=status.HTTP_402_PAYMENT_REQUIRED,
                detail=f"Nicht genug Guthaben auf Stripe-Konto für Rückerstattung. Bitte führen Sie die Rückzahlung manuell durch. Stripe-Fehler: {error_message}"
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Stripe-Fehler bei Rückerstattung: {error_message}"
            )
    except stripe.error.StripeError as e:
        error_message = str(e)
        if "insufficient" in error_message.lower() or "balance" in error_message.lower():
            raise HTTPException(
                status_code=status.HTTP_402_PAYMENT_REQUIRED,
                detail=f"Nicht genug Guthaben auf Stripe-Konto für Rückerstattung. Bitte führen Sie die Rückzahlung manuell durch. Stripe-Fehler: {error_message}"
            )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Stripe-Fehler bei Rückerstattung: {error_message}"
        )

