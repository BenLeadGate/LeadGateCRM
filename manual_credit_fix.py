#!/usr/bin/env python3
"""
Manuelle Gutschrift für eine Stripe-Zahlung
Verwende dies, wenn der Webhook nicht funktioniert hat
"""

import sys
from backend.database import SessionLocal
from backend.models import Makler, MaklerCredits

if len(sys.argv) < 3:
    print("Verwendung: python manual_credit_fix.py <makler_email> <betrag> [payment_intent_id]")
    print("Beispiel: python manual_credit_fix.py juraj@gmx.de 1.0 pi_1234567890")
    sys.exit(1)

makler_email = sys.argv[1]
betrag = float(sys.argv[2])
payment_intent_id = sys.argv[3] if len(sys.argv) > 3 else None

db = SessionLocal()

makler = db.query(Makler).filter(Makler.email == makler_email).first()

if not makler:
    print(f"Makler mit E-Mail {makler_email} nicht gefunden!")
    db.close()
    sys.exit(1)

# Prüfe ob bereits eine Transaktion für diesen Payment Intent existiert
if payment_intent_id:
    existing = (
        db.query(MaklerCredits)
        .filter(MaklerCredits.zahlungsreferenz == payment_intent_id)
        .first()
    )
    
    if existing:
        print(f"Transaktion für Payment Intent {payment_intent_id} existiert bereits!")
        print(f"  Betrag: {existing.betrag} €")
        print(f"  Erstellt: {existing.erstellt_am}")
        db.close()
        sys.exit(0)

# Erstelle Credits-Transaktion
transaktion = MaklerCredits(
    makler_id=makler.id,
    betrag=betrag,
    transaktionstyp="zahlung_online",
    beschreibung=f"Manuelle Gutschrift für Stripe-Zahlung - {betrag:.2f}€",
    zahlungsreferenz=payment_intent_id,
    zahlungsstatus="completed"
)

db.add(transaktion)
db.commit()
db.refresh(transaktion)

print(f"Credits erfolgreich gutgeschrieben!")
print(f"  Makler: {makler.firmenname}")
print(f"  Betrag: {betrag} €")
print(f"  Transaktion ID: {transaktion.id}")
if payment_intent_id:
    print(f"  Payment Intent: {payment_intent_id}")

db.close()








