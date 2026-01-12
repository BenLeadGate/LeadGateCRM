"""
Skript zum Reparieren der Rollen-Werte in der Datenbank.
"""
import sqlite3
import os

def fix_roles():
    """Repariert die Rollen-Werte in der Datenbank."""
    db_path = os.path.join(os.path.dirname(__file__), "leadgate.db")
    
    if not os.path.exists(db_path):
        print("Datenbank nicht gefunden!")
        return
    
    # Mapping von möglichen Werten zu korrekten Werten
    role_mapping = {
        'telefonist': 'telefonist',
        'TELEFONIST': 'telefonist',
        'admin': 'admin',
        'ADMIN': 'admin',
        'manager': 'manager',
        'MANAGER': 'manager',
        'buchhalter': 'buchhalter',
        'BUCHHALTER': 'buchhalter',
    }
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Hole alle Benutzer mit ihren Rollen
        cursor.execute("SELECT id, username, role FROM users")
        users = cursor.fetchall()
        
        print("Repariere Rollen-Werte...")
        updates = 0
        
        for user_id, username, role in users:
            if role:
                # Normalisiere den Rollen-Wert
                normalized_role = role_mapping.get(role, 'telefonist')
                
                if normalized_role != role:
                    print(f"  {username}: '{role}' -> '{normalized_role}'")
                    cursor.execute(
                        "UPDATE users SET role = ? WHERE id = ?",
                        (normalized_role, user_id)
                    )
                    updates += 1
                else:
                    print(f"  {username}: '{role}' (bereits korrekt)")
        
        conn.commit()
        conn.close()
        
        print(f"\n{updates} Rollen-Werte wurden aktualisiert.")
        print("Die Datenbank wurde repariert!")
        
    except Exception as e:
        print(f"Fehler: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    fix_roles()
