#!/usr/bin/env python3
"""Prüft ob Stripe Live-Keys geladen werden"""

from backend.config import STRIPE_ENABLED, STRIPE_SECRET_KEY, STRIPE_PUBLISHABLE_KEY

print("=== Stripe-Konfiguration ===")
print(f"STRIPE_ENABLED: {STRIPE_ENABLED}")
print(f"Secret Key vorhanden: {bool(STRIPE_SECRET_KEY)}")
print(f"Publishable Key vorhanden: {bool(STRIPE_PUBLISHABLE_KEY)}")

if STRIPE_SECRET_KEY:
    print(f"\nSecret Key (erste 20 Zeichen): {STRIPE_SECRET_KEY[:20]}...")
    print(f"Secret Key ist LIVE: {'sk_live_' in STRIPE_SECRET_KEY}")
    print(f"Secret Key ist TEST: {'sk_test_' in STRIPE_SECRET_KEY}")

if STRIPE_PUBLISHABLE_KEY:
    print(f"\nPublishable Key (erste 20 Zeichen): {STRIPE_PUBLISHABLE_KEY[:20]}...")
    print(f"Publishable Key ist LIVE: {'pk_live_' in STRIPE_PUBLISHABLE_KEY}")
    print(f"Publishable Key ist TEST: {'pk_test_' in STRIPE_PUBLISHABLE_KEY}")

if STRIPE_ENABLED:
    if 'sk_live_' in (STRIPE_SECRET_KEY or '') and 'pk_live_' in (STRIPE_PUBLISHABLE_KEY or ''):
        print("\n[OK] LIVE-Modus aktiviert!")
    elif 'sk_test_' in (STRIPE_SECRET_KEY or '') and 'pk_test_' in (STRIPE_PUBLISHABLE_KEY or ''):
        print("\n[WARNUNG] TEST-Modus aktiv - wechsle zu Live-Keys!")
    else:
        print("\n[FEHLER] Keys sind weder Test noch Live!")








