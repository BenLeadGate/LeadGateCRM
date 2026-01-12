#!/usr/bin/env python3
"""Prüft Credits-Stand und Transaktionen"""

from backend.database import SessionLocal
from backend.models import Makler, MaklerCredits
from backend.services.credits_service import berechne_credits_stand

db = SessionLocal()

makler = db.query(Makler).filter(Makler.email == 'juraj@gmx.de').first()

if makler:
    print(f'Makler: {makler.firmenname}')
    print(f'Credits-Stand: {berechne_credits_stand(db, makler.id)} €')
    
    transaktionen = (
        db.query(MaklerCredits)
        .filter(MaklerCredits.makler_id == makler.id)
        .order_by(MaklerCredits.erstellt_am.desc())
        .limit(10)
        .all()
    )
    
    print(f'\nLetzte 10 Transaktionen:')
    for t in transaktionen:
        print(f'  {t.erstellt_am}: {t.betrag:+.2f} € - {t.transaktionstyp} - {t.beschreibung or ""}')
        if t.payment_intent_id:
            print(f'    Payment Intent: {t.payment_intent_id}')
else:
    print('Makler nicht gefunden')

db.close()








