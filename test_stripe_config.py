#!/usr/bin/env python3
"""Test-Skript um Stripe-Konfiguration zu prüfen"""

import os

# Versuche python-dotenv zu laden
try:
    from dotenv import load_dotenv
    load_dotenv()
    print("[OK] python-dotenv geladen")
except ImportError:
    print("[FEHLER] python-dotenv NICHT installiert!")
    print("  Installiere mit: pip install python-dotenv")

# Prüfe Stripe-Keys
print("\n=== Stripe-Konfiguration ===")
secret_key = os.getenv("STRIPE_SECRET_KEY")
publishable_key = os.getenv("STRIPE_PUBLISHABLE_KEY")

print(f"STRIPE_SECRET_KEY vorhanden: {bool(secret_key)}")
if secret_key:
    print(f"  Länge: {len(secret_key)}")
    print(f"  Erste 20 Zeichen: {secret_key[:20]}...")
    print(f"  Letzte 10 Zeichen: ...{secret_key[-10:]}")
else:
    print("  [FEHLER] Secret Key NICHT gefunden!")

print(f"\nSTRIPE_PUBLISHABLE_KEY vorhanden: {bool(publishable_key)}")
if publishable_key:
    print(f"  Länge: {len(publishable_key)}")
    print(f"  Erste 20 Zeichen: {publishable_key[:20]}...")
else:
    print("  [FEHLER] Publishable Key NICHT gefunden!")

# Prüfe ob Stripe aktiviert wäre
stripe_enabled = secret_key is not None and publishable_key is not None
print(f"\nSTRIPE_ENABLED würde sein: {stripe_enabled}")

if not stripe_enabled:
    print("\n[WARNUNG] PROBLEM: Stripe ist NICHT aktiviert!")
    print("\nMögliche Lösungen:")
    print("1. Prüfe ob .env-Datei im Projektordner existiert")
    print("2. Prüfe ob beide Keys in .env-Datei vorhanden sind")
    print("3. Starte den Server neu (uvicorn backend.main:app --reload)")
else:
    print("\n[OK] Stripe ist konfiguriert und sollte funktionieren!")

