"""
Skript zum Auflisten aller Benutzer in der Datenbank.
"""
import sys
import os
import sqlite3

def list_users():
    """Listet alle Benutzer in der Datenbank auf."""
    db_path = os.path.join(os.path.dirname(__file__), "leadgate.db")
    
    if not os.path.exists(db_path):
        print("Datenbank nicht gefunden. Standard-Benutzer wird beim Serverstart erstellt:")
        print("  Benutzername: ben")
        print("  Passwort: admin123")
        print("  Rolle: admin")
        return
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Prüfe ob users-Tabelle existiert
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='users'")
        if not cursor.fetchone():
            print("Users-Tabelle nicht gefunden. Standard-Benutzer wird beim Serverstart erstellt:")
            print("  Benutzername: ben")
            print("  Passwort: admin123")
            print("  Rolle: admin")
            conn.close()
            return
        
        # Hole alle Benutzer
        cursor.execute("SELECT id, username, email, is_active, role, created_at FROM users")
        users = cursor.fetchall()
        
        if not users:
            print("Keine Benutzer in der Datenbank gefunden.")
            print("\nStandard-Benutzer wird beim Serverstart erstellt:")
            print("  Benutzername: ben")
            print("  Passwort: admin123")
            print("  Rolle: admin")
            conn.close()
            return
        
        print("=" * 60)
        print("Benutzer in der Datenbank:")
        print("=" * 60)
        
        for user in users:
            user_id, username, email, is_active, role, created_at = user
            status = "Aktiv" if is_active else "Inaktiv"
            role_str = role if role else "telefonist"
            
            print(f"\nBenutzername: {username}")
            print(f"  E-Mail: {email}")
            print(f"  Rolle: {role_str}")
            print(f"  Status: {status}")
            if created_at:
                print(f"  Erstellt: {created_at}")
        
        print("\n" + "=" * 60)
        print("\nHinweis: Passwörter werden nicht im Klartext gespeichert.")
        print("Standard-Passwort für 'ben': admin123")
        print("=" * 60)
        
        conn.close()
        
    except Exception as e:
        print(f"Fehler beim Lesen der Benutzer: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    list_users()
