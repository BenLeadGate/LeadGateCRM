from typing import List, Optional
from datetime import datetime
from sqlalchemy import func

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from .. import schemas
from ..database import get_db
from ..models import Makler, MaklerCredits, User, CreditsRueckzahlungAnfrage, ChatMessage
from ..models.user import UserRole
from ..services.auth_service import get_current_active_user, require_admin_or_manager


router = APIRouter()


def berechne_credits_stand(db: Session, makler_id: int) -> float:
    """
    Berechnet den aktuellen Credits-Stand eines Maklers.
    Summiert alle Transaktionen (positive = Aufladung, negative = Abbuchung).
    """
    result = db.query(func.sum(MaklerCredits.betrag)).filter(
        MaklerCredits.makler_id == makler_id
    ).scalar()
    
    return float(result) if result is not None else 0.0


@router.get("/makler/{makler_id}/credits/stand", response_model=schemas.MaklerCreditsStand)
def get_credits_stand(
    makler_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Gibt den aktuellen Credits-Stand eines Maklers zurück.
    """
    makler = db.query(Makler).filter(Makler.id == makler_id).first()
    if not makler:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Makler nicht gefunden"
        )
    
    aktueller_stand = berechne_credits_stand(db, makler_id)
    
    # Hole letzte Transaktion
    letzte_transaktion = (
        db.query(MaklerCredits)
        .filter(MaklerCredits.makler_id == makler_id)
        .order_by(MaklerCredits.erstellt_am.desc())
        .first()
    )
    
    # Zähle Transaktionen
    transaktionsanzahl = (
        db.query(MaklerCredits)
        .filter(MaklerCredits.makler_id == makler_id)
        .count()
    )
    
    return schemas.MaklerCreditsStand(
        makler_id=makler_id,
        aktueller_stand=aktueller_stand,
        letzte_transaktion_am=letzte_transaktion.erstellt_am if letzte_transaktion else None,
        transaktionsanzahl=transaktionsanzahl
    )


@router.get("/makler/{makler_id}/credits/historie", response_model=List[schemas.MaklerCreditsRead])
def get_credits_historie(
    makler_id: int,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Gibt die Credits-Transaktionshistorie eines Maklers zurück.
    """
    makler = db.query(Makler).filter(Makler.id == makler_id).first()
    if not makler:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Makler nicht gefunden"
        )
    
    transaktionen = (
        db.query(MaklerCredits)
        .filter(MaklerCredits.makler_id == makler_id)
        .order_by(MaklerCredits.erstellt_am.desc())
        .limit(limit)
        .all()
    )
    
    return transaktionen


@router.post("/makler/{makler_id}/credits/aufladen", response_model=schemas.MaklerCreditsRead)
def credits_aufladen(
    makler_id: int,
    data: schemas.MaklerCreditsAufladen,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin_or_manager)
):
    """
    Lädt Credits für einen Makler auf (nur für Admin oder Manager).
    """
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
    
    # Erstelle Transaktion
    transaktion = MaklerCredits(
        makler_id=makler_id,
        betrag=data.betrag,
        transaktionstyp="aufladung",
        beschreibung=data.beschreibung or f"Manuelle Aufladung durch {current_user.username}",
        erstellt_von_user_id=current_user.id
    )
    
    db.add(transaktion)
    db.commit()
    db.refresh(transaktion)
    
    return transaktion


@router.post("/makler/{makler_id}/credits/manuelle-anpassung", response_model=schemas.MaklerCreditsRead)
def credits_manuelle_anpassung(
    makler_id: int,
    data: schemas.MaklerCreditsAufladen,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin_or_manager)
):
    """
    Manuelle Anpassung der Credits (kann auch negativ sein für Korrekturen).
    Nur für Admin oder Manager.
    """
    makler = db.query(Makler).filter(Makler.id == makler_id).first()
    if not makler:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Makler nicht gefunden"
        )
    
    if data.betrag == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Betrag darf nicht 0 sein"
        )
    
    # Erstelle Transaktion
    transaktion = MaklerCredits(
        makler_id=makler_id,
        betrag=data.betrag,
        transaktionstyp="manuelle_anpassung",
        beschreibung=data.beschreibung or f"Manuelle Anpassung durch {current_user.username}",
        erstellt_von_user_id=current_user.id
    )
    
    db.add(transaktion)
    db.commit()
    db.refresh(transaktion)
    
    return transaktion


@router.get("/makler/{makler_id}/credits/rueckzahlbar")
def get_rueckzahlbare_credits(
    makler_id: int,
    monate: int = 2,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Gibt eine Liste von Credits zurück, die zurückgezahlt werden können.
    Credits können zurückgezahlt werden, wenn sie älter als X Monate sind und noch nicht verwendet wurden.
    """
    from ..services.credits_service import berechne_rueckzahlbare_credits
    
    makler = db.query(Makler).filter(Makler.id == makler_id).first()
    if not makler:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Makler nicht gefunden"
        )
    
    if (makler.rechnungssystem_typ or 'alt') != 'neu':
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Dieser Makler verwendet nicht das Credits-System"
        )
    
    rueckzahlbare = berechne_rueckzahlbare_credits(db, makler_id, monate)
    return rueckzahlbare


@router.get("/credits/rueckzahlung/anfragen", response_model=List[schemas.CreditsRueckzahlungAnfrageRead])
def get_rueckzahlung_anfragen(
    status: Optional[str] = None,  # "pending", "approved", "rejected" oder None für alle
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin_or_manager)
):
    """
    Gibt alle Rückzahlungsanfragen zurück.
    Nur für Admin oder Manager.
    """
    from ..models import CreditsRueckzahlungAnfrage
    
    query = db.query(CreditsRueckzahlungAnfrage)
    
    if status:
        query = query.filter(CreditsRueckzahlungAnfrage.status == status)
    
    anfragen = query.order_by(CreditsRueckzahlungAnfrage.erstellt_am.desc()).all()
    
    result = []
    for anfrage in anfragen:
        anfrage_dict = {
            "id": anfrage.id,
            "makler_id": anfrage.makler_id,
            "transaktion_id": anfrage.transaktion_id,
            "betrag": anfrage.betrag,
            "status": anfrage.status,
            "beschreibung": anfrage.beschreibung,
            "erstellt_am": anfrage.erstellt_am,
            "bearbeitet_am": anfrage.bearbeitet_am,
            "bearbeitet_von_user_id": anfrage.bearbeitet_von_user_id,
            "rueckzahlung_transaktion_id": anfrage.rueckzahlung_transaktion_id,
            "rueckzahlung_status": getattr(anfrage, 'rueckzahlung_status', None),
            "stripe_refund_id": getattr(anfrage, 'stripe_refund_id', None),
            "makler_firmenname": anfrage.makler.firmenname if anfrage.makler else None,
            "bearbeitet_von_username": anfrage.bearbeitet_von_user.username if anfrage.bearbeitet_von_user else None
        }
        result.append(anfrage_dict)
    
    return result


@router.post("/credits/rueckzahlung/anfrage/{anfrage_id}/bearbeiten", response_model=schemas.CreditsRueckzahlungAnfrageRead)
def bearbeite_rueckzahlung_anfrage(
    anfrage_id: int,
    data: schemas.CreditsRueckzahlungAnfrageBearbeitung,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin_or_manager)
):
    """
    Bearbeitet eine Rückzahlungsanfrage (Genehmigung oder Ablehnung).
    Nur für Admin oder Manager.
    """
    from ..models import CreditsRueckzahlungAnfrage, ChatMessage
    from ..services.credits_service import erstelle_rueckzahlung
    
    anfrage = db.query(CreditsRueckzahlungAnfrage).filter(CreditsRueckzahlungAnfrage.id == anfrage_id).first()
    if not anfrage:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Anfrage nicht gefunden"
        )
    
    if anfrage.status != "pending":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Anfrage wurde bereits bearbeitet (Status: {anfrage.status})"
        )
    
    if data.status not in ["approved", "rejected"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Status muss 'approved' oder 'rejected' sein"
        )
    
    # Aktualisiere Anfrage
    anfrage.status = data.status
    anfrage.bearbeitet_am = datetime.utcnow()
    anfrage.bearbeitet_von_user_id = current_user.id
    
    # Wenn genehmigt: Setze Status, aber führe Rückzahlung NICHT automatisch durch
    if data.status == "approved":
        # Setze Status auf "genehmigt" - Rückzahlung wird erst nach Bestätigung durchgeführt
        anfrage.rueckzahlung_status = "genehmigt"
    
    db.commit()
    db.refresh(anfrage)
    
    # Sende Chat-Nachricht an Makler
    status_text = "genehmigt" if data.status == "approved" else "abgelehnt"
    nachricht = (
        f"💰 Rückzahlungsanfrage #{anfrage_id}\n\n"
        f"Status: {status_text.upper()}\n"
        f"Betrag: {anfrage.betrag:.2f} €\n\n"
        f"{data.beschreibung or 'Keine zusätzliche Beschreibung'}"
    )
    
    chat_message = ChatMessage(
        from_user_id=current_user.id,
        to_makler_id=anfrage.makler_id,
        nachricht=nachricht,
        gelesen=False
    )
    db.add(chat_message)
    db.commit()
    
    # Lade zusätzliche Informationen
    return schemas.CreditsRueckzahlungAnfrageRead(
        id=anfrage.id,
        makler_id=anfrage.makler_id,
        transaktion_id=anfrage.transaktion_id,
        betrag=anfrage.betrag,
        status=anfrage.status,
        beschreibung=anfrage.beschreibung,
        erstellt_am=anfrage.erstellt_am,
        bearbeitet_am=anfrage.bearbeitet_am,
        bearbeitet_von_user_id=anfrage.bearbeitet_von_user_id,
        rueckzahlung_transaktion_id=anfrage.rueckzahlung_transaktion_id,
        makler_firmenname=anfrage.makler.firmenname if anfrage.makler else None,
        bearbeitet_von_username=current_user.username
    )


@router.post("/credits/rueckzahlung/anfrage/{anfrage_id}/durchfuehren", response_model=schemas.CreditsRueckzahlungAnfrageRead)
def fuehre_rueckzahlung_durch(
    anfrage_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin_or_manager)
):
    """
    Führt eine genehmigte Rückzahlung tatsächlich durch.
    Erstellt die Transaktion und führt ggf. Stripe-Refund durch.
    Nur für Admin oder Manager.
    """
    from ..services.credits_service import erstelle_rueckzahlung
    
    anfrage = db.query(CreditsRueckzahlungAnfrage).filter(CreditsRueckzahlungAnfrage.id == anfrage_id).first()
    if not anfrage:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Anfrage nicht gefunden"
        )
    
    if anfrage.status != "approved":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Nur genehmigte Anfragen können durchgeführt werden"
        )
    
    if anfrage.rueckzahlung_status not in ["genehmigt", None]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Rückzahlung wurde bereits durchgeführt (Status: {anfrage.rueckzahlung_status})"
        )
    
    try:
        # Erstelle System-Transaktion (Credits werden abgebucht)
        rueckzahlung = erstelle_rueckzahlung(
            db=db,
            makler=anfrage.makler,
            transaktion_id=anfrage.transaktion_id,
            betrag=anfrage.betrag,
            beschreibung=f"Rückzahlung durchgeführt (Anfrage #{anfrage_id})"
        )
        anfrage.rueckzahlung_transaktion_id = rueckzahlung.id
        
        # Prüfe ob ursprüngliche Zahlung über Stripe war
        ursprüngliche_transaktion = (
            db.query(MaklerCredits)
            .filter(MaklerCredits.id == anfrage.transaktion_id)
            .first()
        )
        
        if ursprüngliche_transaktion and ursprüngliche_transaktion.zahlungsreferenz:
            # Versuche automatische Stripe-Rückerstattung
            # WICHTIG: Ziehe Stripe-Gebühren (2.9% + 30 Cent) vom Rückzahlungsbetrag ab
            try:
                from ..services.stripe_service import create_refund, berechne_stripe_gebuehren, berechne_rueckzahlungsbetrag_abzueglich_gebuehren
                
                ursprünglicher_betrag = anfrage.betrag
                gebuehren = berechne_stripe_gebuehren(ursprünglicher_betrag)
                rueckzahlungsbetrag = berechne_rueckzahlungsbetrag_abzueglich_gebuehren(ursprünglicher_betrag)
                
                # Erstelle Refund mit reduziertem Betrag (abzüglich Gebühren)
                refund = create_refund(
                    payment_intent_id=ursprüngliche_transaktion.zahlungsreferenz,
                    betrag=rueckzahlungsbetrag,
                    beschreibung=f"Rückerstattung für Anfrage #{anfrage_id} (abzüglich Stripe-Gebühren: {gebuehren:.2f}€)"
                )
                anfrage.stripe_refund_id = refund["id"]
                anfrage.rueckzahlung_status = "stripe_refund_completed" if refund["status"] == "succeeded" else "stripe_refund_pending"
                
                # Aktualisiere Beschreibung mit Gebühren-Info
                if not anfrage.beschreibung:
                    anfrage.beschreibung = ""
                anfrage.beschreibung += f"\n[Stripe-Gebühren abgezogen: {gebuehren:.2f}€, Rückzahlungsbetrag: {rueckzahlungsbetrag:.2f}€]"
            except HTTPException as stripe_error:
                # Stripe-Refund fehlgeschlagen, manuelle Rückzahlung erforderlich
                anfrage.rueckzahlung_status = "zurueckzuzahlen"
                error_detail = stripe_error.detail if hasattr(stripe_error, 'detail') else str(stripe_error)
                print(f"Stripe-Refund fehlgeschlagen für Anfrage #{anfrage_id}: {error_detail}")
                # Speichere Fehler in Beschreibung für spätere Referenz
                if not anfrage.beschreibung:
                    anfrage.beschreibung = ""
                anfrage.beschreibung += f"\n[Stripe-Fehler: {error_detail}]"
            except Exception as stripe_error:
                # Stripe-Refund fehlgeschlagen, manuelle Rückzahlung erforderlich
                anfrage.rueckzahlung_status = "zurueckzuzahlen"
                error_detail = str(stripe_error)
                print(f"Stripe-Refund fehlgeschlagen für Anfrage #{anfrage_id}: {error_detail}")
                # Speichere Fehler in Beschreibung für spätere Referenz
                if not anfrage.beschreibung:
                    anfrage.beschreibung = ""
                anfrage.beschreibung += f"\n[Stripe-Fehler: {error_detail}]"
        else:
            # Keine Stripe-Zahlung, manuelle Rückzahlung erforderlich
            anfrage.rueckzahlung_status = "zurueckzuzahlen"
        
        db.commit()
        db.refresh(anfrage)
        
        # Sende Chat-Nachricht an Makler
        status_text = "automatisch über Stripe zurückgezahlt" if anfrage.rueckzahlung_status == "stripe_refund_completed" else "zurückzuzahlen (manuell)"
        
        # Berechne tatsächlichen Rückzahlungsbetrag für Chat-Nachricht
        gebuehren_text = ""
        if ursprüngliche_transaktion and ursprüngliche_transaktion.zahlungsreferenz:
            from ..services.stripe_service import berechne_stripe_gebuehren, berechne_rueckzahlungsbetrag_abzueglich_gebuehren
            gebuehren = berechne_stripe_gebuehren(anfrage.betrag)
            tatsaechlicher_rueckzahlungsbetrag = berechne_rueckzahlungsbetrag_abzueglich_gebuehren(anfrage.betrag)
            if anfrage.rueckzahlung_status == "stripe_refund_completed":
                gebuehren_text = f"\n\nStripe-Gebühren (2.9% + 30 Cent): -{gebuehren:.2f} €\nTatsächlicher Rückzahlungsbetrag: {tatsaechlicher_rueckzahlungsbetrag:.2f} €"
            else:
                gebuehren_text = f"\n\nHinweis: Bei Stripe-Rückzahlung werden Gebühren (2.9% + 30 Cent = {gebuehren:.2f} €) abgezogen."
        
        nachricht = (
            f"💰 Rückzahlungsanfrage #{anfrage_id}\n\n"
            f"Rückzahlung wurde durchgeführt.\n"
            f"Status: {status_text}\n"
            f"Ursprünglicher Betrag: {anfrage.betrag:.2f} €{gebuehren_text}\n\n"
            f"Die Credits wurden von Ihrem Konto abgebucht."
        )
        
        chat_message = ChatMessage(
            from_user_id=current_user.id,
            to_makler_id=anfrage.makler_id,
            nachricht=nachricht,
            gelesen=False
        )
        db.add(chat_message)
        db.commit()
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Fehler bei Rückzahlung: {str(e)}"
        )
    
    return schemas.CreditsRueckzahlungAnfrageRead(
        id=anfrage.id,
        makler_id=anfrage.makler_id,
        transaktion_id=anfrage.transaktion_id,
        betrag=anfrage.betrag,
        status=anfrage.status,
        beschreibung=anfrage.beschreibung,
        erstellt_am=anfrage.erstellt_am,
        bearbeitet_am=anfrage.bearbeitet_am,
        bearbeitet_von_user_id=anfrage.bearbeitet_von_user_id,
        rueckzahlung_transaktion_id=anfrage.rueckzahlung_transaktion_id,
        rueckzahlung_status=getattr(anfrage, 'rueckzahlung_status', None),
        stripe_refund_id=getattr(anfrage, 'stripe_refund_id', None),
        makler_firmenname=anfrage.makler.firmenname if anfrage.makler else None,
        bearbeitet_von_username=current_user.username
    )


@router.post("/credits/rueckzahlung/anfrage/{anfrage_id}/als-zurueckgezahlt-markieren", response_model=schemas.CreditsRueckzahlungAnfrageRead)
def markiere_rueckzahlung_als_zurueckgezahlt(
    anfrage_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin_or_manager)
):
    """
    Markiert eine Rückzahlung als manuell zurückgezahlt (nach manueller Überweisung).
    Nur für Admin oder Manager.
    """
    anfrage = db.query(CreditsRueckzahlungAnfrage).filter(CreditsRueckzahlungAnfrage.id == anfrage_id).first()
    if not anfrage:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Anfrage nicht gefunden"
        )
    
    if anfrage.status != "approved":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Nur genehmigte Anfragen können als zurückgezahlt markiert werden"
        )
    
    if anfrage.rueckzahlung_status == "zurueckgezahlt":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Rückzahlung wurde bereits als zurückgezahlt markiert"
        )
    
    if anfrage.rueckzahlung_status not in ["zurueckzuzahlen", "genehmigt"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Rückzahlung muss erst durchgeführt werden (aktueller Status: {anfrage.rueckzahlung_status})"
        )
    
    # Markiere als zurückgezahlt
    anfrage.rueckzahlung_status = "zurueckgezahlt"
    db.commit()
    db.refresh(anfrage)
    
    return schemas.CreditsRueckzahlungAnfrageRead(
        id=anfrage.id,
        makler_id=anfrage.makler_id,
        transaktion_id=anfrage.transaktion_id,
        betrag=anfrage.betrag,
        status=anfrage.status,
        beschreibung=anfrage.beschreibung,
        erstellt_am=anfrage.erstellt_am,
        bearbeitet_am=anfrage.bearbeitet_am,
        bearbeitet_von_user_id=anfrage.bearbeitet_von_user_id,
        rueckzahlung_transaktion_id=anfrage.rueckzahlung_transaktion_id,
        rueckzahlung_status=anfrage.rueckzahlung_status,
        stripe_refund_id=getattr(anfrage, 'stripe_refund_id', None),
        makler_firmenname=anfrage.makler.firmenname if anfrage.makler else None,
        bearbeitet_von_username=current_user.username
    )


@router.post("/makler/{makler_id}/credits/rueckzahlung", response_model=schemas.MaklerCreditsRead)
def erstelle_credits_rueckzahlung(
    makler_id: int,
    data: schemas.CreditsRueckzahlungRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin_or_manager)
):
    """
    Erstellt eine Rückzahlung für nicht verwendete Credits (direkt, ohne Anfrage).
    Nur für Admin oder Manager.
    """
    from ..services.credits_service import erstelle_rueckzahlung
    
    makler = db.query(Makler).filter(Makler.id == makler_id).first()
    if not makler:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Makler nicht gefunden"
        )
    
    if (makler.rechnungssystem_typ or 'alt') != 'neu':
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Dieser Makler verwendet nicht das Credits-System"
        )
    
    try:
        rueckzahlung = erstelle_rueckzahlung(
            db=db,
            makler=makler,
            transaktion_id=data.transaktion_id,
            betrag=data.betrag,
            beschreibung=data.beschreibung or f"Rückzahlung durch {current_user.username}"
        )
        return rueckzahlung
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

