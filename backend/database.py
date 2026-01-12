from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# SQLite-Datenbank lokal im Projektverzeichnis
SQLALCHEMY_DATABASE_URL = "sqlite:///./leadgate.db"

# connect_args notwendig für SQLite bei Nutzung in FastAPI
engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    """
    Abhängigkeits-Funktion für FastAPI,
    stellt pro Request eine neue DB-Session bereit.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """
    Initialisiert die Datenbank und erstellt alle Tabellen.
    Erstellt automatisch den Admin-User "ben" falls er nicht existiert.
    Führt auch Datenbank-Migrationen aus.
    """
    from sqlalchemy import text
    from .models import Makler, Lead, Rechnung, User, ChatMessage, ChatGruppe, ChatGruppeTeilnehmer, MaklerDokument, MaklerCredits, CreditsRueckzahlungAnfrage, Ticket, TicketTeilnehmer  # noqa: F401
    from .models.user import UserRole
    from .services.auth_service import get_password_hash, get_user_by_username
    
    Base.metadata.create_all(bind=engine)
    
    # Migration: Füge 'role' Spalte hinzu falls sie nicht existiert
    db = SessionLocal()
    try:
        # Prüfe ob die Spalte bereits existiert
        result = db.execute(text("PRAGMA table_info(users)"))
        columns = [row[1] for row in result.fetchall()]
        
        if 'role' not in columns:
            print("Führe Migration aus: Füge 'role' Spalte zur users-Tabelle hinzu...")
            # Füge die Spalte hinzu (SQLite unterstützt NOT NULL nicht direkt in ALTER TABLE)
            db.execute(text("ALTER TABLE users ADD COLUMN role VARCHAR(20) DEFAULT 'telefonist'"))
            db.commit()
            
            # Setze alle bestehenden Benutzer auf 'telefonist' falls sie None haben
            db.execute(text("UPDATE users SET role = 'telefonist' WHERE role IS NULL"))
            
            # Setze 'ben' auf 'admin' falls er existiert
            db.execute(text("UPDATE users SET role = 'admin' WHERE username = 'ben'"))
            db.commit()
            print("[OK] 'role' Spalte erfolgreich hinzugefuegt und Rollen aktualisiert")
        
        # Normalisiere Rollen-Werte (korrigiere Groß-/Kleinschreibung)
        cursor = db.execute(text("SELECT id, username, role FROM users"))
        users = cursor.fetchall()
        role_mapping = {
            'TELEFONIST': 'telefonist',
            'ADMIN': 'admin',
            'MANAGER': 'manager',
            'BUCHHALTER': 'buchhalter',
            'UPLOADER': 'uploader',
        }
        updates = 0
        for user_id, username, role in users:
            if role and role in role_mapping:
                normalized = role_mapping[role]
                db.execute(text("UPDATE users SET role = :role WHERE id = :id"), 
                          {"role": normalized, "id": user_id})
                updates += 1
        if updates > 0:
            db.commit()
            print(f"[OK] {updates} Rollen-Werte normalisiert")
    except Exception as e:
        db.rollback()
        print(f"Warnung bei Migration: {e}")
    finally:
        db.close()
    
    # Migration: Füge Tracking-Spalten zur makler-Tabelle hinzu falls sie nicht existieren
    db = SessionLocal()
    try:
        result = db.execute(text("PRAGMA table_info(makler)"))
        columns = [row[1] for row in result.fetchall()]
        
        if 'created_by_user_id' not in columns:
            print("Führe Migration aus: Füge Tracking-Spalten zur makler-Tabelle hinzu...")
            db.execute(text("ALTER TABLE makler ADD COLUMN created_by_user_id INTEGER"))
            db.execute(text("ALTER TABLE makler ADD COLUMN modified_by_user_id INTEGER"))
            db.commit()
            print("[OK] Tracking-Spalten erfolgreich zur makler-Tabelle hinzugefuegt")
    except Exception as e:
        db.rollback()
        print(f"Warnung bei Migration (makler Tracking-Spalten): {e}")
    finally:
        db.close()
    
    # Migration: Füge Gebiet-Spalte zur makler-Tabelle hinzu falls sie nicht existiert
    db = SessionLocal()
    try:
        result = db.execute(text("PRAGMA table_info(makler)"))
        columns = [row[1] for row in result.fetchall()]
        
        if 'gebiet' not in columns:
            print("Führe Migration aus: Füge Gebiet-Spalte zur makler-Tabelle hinzu...")
            db.execute(text("ALTER TABLE makler ADD COLUMN gebiet VARCHAR"))
            db.commit()
            print("[OK] Gebiet-Spalte erfolgreich zur makler-Tabelle hinzugefuegt")
    except Exception as e:
        db.rollback()
        print(f"Warnung bei Migration (makler Gebiet-Spalte): {e}")
    finally:
        db.close()
    
    # Migration: Füge GateLink-Passwort-Spalte zur makler-Tabelle hinzu falls sie nicht existiert
    db = SessionLocal()
    try:
        result = db.execute(text("PRAGMA table_info(makler)"))
        columns = [row[1] for row in result.fetchall()]
        
        if 'gatelink_password' not in columns:
            print("Fuehre Migration aus: Fuege GateLink-Passwort-Spalte zur makler-Tabelle hinzu...")
            db.execute(text("ALTER TABLE makler ADD COLUMN gatelink_password VARCHAR"))
            db.commit()
            print("[OK] GateLink-Passwort-Spalte erfolgreich zur makler-Tabelle hinzugefuegt")
    except Exception as e:
        db.rollback()
        print(f"Warnung bei Migration (makler GateLink-Passwort): {e}")
    finally:
        db.close()
    
    # Migration: Füge Tracking-Spalte zur rechnungen-Tabelle hinzu falls sie nicht existiert
    db = SessionLocal()
    try:
        result = db.execute(text("PRAGMA table_info(rechnungen)"))
        columns = [row[1] for row in result.fetchall()]
        
        if 'created_by_user_id' not in columns:
            print("Führe Migration aus: Füge Tracking-Spalte zur rechnungen-Tabelle hinzu...")
            db.execute(text("ALTER TABLE rechnungen ADD COLUMN created_by_user_id INTEGER"))
            db.commit()
            print("[OK] Tracking-Spalte erfolgreich zur rechnungen-Tabelle hinzugefuegt")
    except Exception as e:
        db.rollback()
        print(f"Warnung bei Migration (rechnungen Tracking-Spalte): {e}")
    finally:
        db.close()
    
    # Migration: Füge Tracking-Spalte zur leads-Tabelle hinzu falls sie nicht existiert
    db = SessionLocal()
    try:
        result = db.execute(text("PRAGMA table_info(leads)"))
        columns = [row[1] for row in result.fetchall()]
        
        if 'created_by_user_id' not in columns:
            print("Führe Migration aus: Füge Tracking-Spalte zur leads-Tabelle hinzu...")
            db.execute(text("ALTER TABLE leads ADD COLUMN created_by_user_id INTEGER"))
            db.commit()
            print("[OK] Tracking-Spalte erfolgreich zur leads-Tabelle hinzugefuegt")
    except Exception as e:
        db.rollback()
        print(f"Warnung bei Migration (leads Tracking-Spalte): {e}")
    finally:
        db.close()
    
    # Migration: Füge Lead-Detail-Spalten zur leads-Tabelle hinzu falls sie nicht existieren
    db = SessionLocal()
    try:
        result = db.execute(text("PRAGMA table_info(leads)"))
        columns = [row[1] for row in result.fetchall()]
        
        new_columns = {
            'anbieter_name': 'VARCHAR',
            'postleitzahl': 'VARCHAR',
            'ort': 'VARCHAR',
            'grundstuecksflaeche': 'REAL',
            'wohnflaeche': 'REAL',
            'telefonnummer': 'VARCHAR',
            'features': 'VARCHAR',
            'beschreibung': 'VARCHAR',
            'moegliche_makler_ids': 'VARCHAR',
            'kontakt_datum': 'DATE',
            'kontakt_zeitraum': 'VARCHAR',
            'qualifiziert_am': 'DATETIME'
        }
        
        added_columns = []
        for col_name, col_type in new_columns.items():
            if col_name not in columns:
                db.execute(text(f"ALTER TABLE leads ADD COLUMN {col_name} {col_type}"))
                added_columns.append(col_name)
        
        if added_columns:
            db.commit()
            print(f"[OK] Lead-Detail-Spalten erfolgreich hinzugefuegt: {', '.join(added_columns)}")
    except Exception as e:
        db.rollback()
        print(f"Warnung bei Migration (leads Detail-Spalten): {e}")
    finally:
        db.close()
    
    # Migration: Füge qualifiziert_von_user_id zur leads-Tabelle hinzu falls sie nicht existiert
    db = SessionLocal()
    try:
        result = db.execute(text("PRAGMA table_info(leads)"))
        columns = [row[1] for row in result.fetchall()]
        
        if 'qualifiziert_von_user_id' not in columns:
            print("Fuehre Migration aus: Fuege qualifiziert_von_user_id zur leads-Tabelle hinzu...")
            db.execute(text("ALTER TABLE leads ADD COLUMN qualifiziert_von_user_id INTEGER"))
            db.execute(text("CREATE INDEX IF NOT EXISTS idx_leads_qualifiziert_von_user_id ON leads(qualifiziert_von_user_id)"))
            db.commit()
            print("[OK] qualifiziert_von_user_id erfolgreich zur leads-Tabelle hinzugefuegt")
    except Exception as e:
        db.rollback()
        print(f"Warnung bei Migration (qualifiziert_von_user_id): {e}")
    finally:
        db.close()
    
    # Migration: Füge Makler-spezifische Felder zur leads-Tabelle hinzu falls sie nicht existieren
    db = SessionLocal()
    try:
        result = db.execute(text("PRAGMA table_info(leads)"))
        columns = [row[1] for row in result.fetchall()]
        
        if 'makler_status' not in columns:
            print("Fuehre Migration aus: Fuege Makler-Status-Spalte zur leads-Tabelle hinzu...")
            db.execute(text("ALTER TABLE leads ADD COLUMN makler_status VARCHAR"))
            db.commit()
            print("[OK] Makler-Status-Spalte erfolgreich zur leads-Tabelle hinzugefuegt")
        
        if 'makler_beschreibung' not in columns:
            print("Fuehre Migration aus: Fuege Makler-Beschreibung-Spalte zur leads-Tabelle hinzu...")
            db.execute(text("ALTER TABLE leads ADD COLUMN makler_beschreibung VARCHAR"))
            db.commit()
            print("[OK] Makler-Beschreibung-Spalte erfolgreich zur leads-Tabelle hinzugefuegt")
        
        if 'makler_status_geaendert_am' not in columns:
            print("Fuehre Migration aus: Fuege Makler-Status-Geaendert-Spalte zur leads-Tabelle hinzu...")
            db.execute(text("ALTER TABLE leads ADD COLUMN makler_status_geaendert_am DATETIME"))
            db.commit()
            print("[OK] Makler-Status-Geaendert-Spalte erfolgreich zur leads-Tabelle hinzugefuegt")
    except Exception as e:
        db.rollback()
        print(f"Warnung bei Migration (leads Makler-Felder): {e}")
    finally:
        db.close()
    
    # Migration: Mache makler_id optional (nullable)
    # SQLite unterstützt ALTER COLUMN nicht direkt, daher müssen wir die Tabelle neu erstellen
    db = SessionLocal()
    try:
        result = db.execute(text("PRAGMA table_info(leads)"))
        columns_info = result.fetchall()
        
        # Prüfe ob makler_id NOT NULL ist
        makler_id_col = next((col for col in columns_info if col[1] == 'makler_id'), None)
        if makler_id_col and makler_id_col[3] == 1:  # 3 = notnull flag (1 = NOT NULL, 0 = NULL allowed)
            print("Führe Migration aus: Mache makler_id optional...")
            
            # Erstelle Backup-Tabelle
            db.execute(text("""
                CREATE TABLE IF NOT EXISTS leads_backup AS 
                SELECT * FROM leads
            """))
            
            # Lösche alte Tabelle
            db.execute(text("DROP TABLE IF EXISTS leads"))
            
            # Erstelle neue Tabelle mit nullable makler_id
            db.execute(text("""
                CREATE TABLE leads (
                    id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
                    makler_id INTEGER,
                    erstellt_am DATETIME NOT NULL,
                    status VARCHAR(20) NOT NULL DEFAULT 'unqualifiziert',
                    created_by_user_id INTEGER,
                    anbieter_name VARCHAR,
                    postleitzahl VARCHAR,
                    ort VARCHAR,
                    grundstuecksflaeche REAL,
                    wohnflaeche REAL,
                    telefonnummer VARCHAR,
                    features VARCHAR,
                    beschreibung VARCHAR,
                    moegliche_makler_ids VARCHAR,
                    FOREIGN KEY(makler_id) REFERENCES makler (id),
                    FOREIGN KEY(created_by_user_id) REFERENCES users (id)
                )
            """))
            
            # Migriere Daten zurück
            db.execute(text("""
                INSERT INTO leads 
                SELECT * FROM leads_backup
            """))
            
            # Lösche Backup-Tabelle
            db.execute(text("DROP TABLE IF EXISTS leads_backup"))
            
            db.commit()
            print("[OK] makler_id ist jetzt optional - Migration erfolgreich")
        else:
            print("[OK] makler_id ist bereits optional")
    except Exception as e:
        db.rollback()
        print(f"Warnung bei Migration (makler_id nullable): {e}")
        # Versuche es mit einem einfacheren Ansatz - setze NULL-Werte für fehlende makler_id
        try:
            # Für den Fall, dass die Migration fehlschlägt, setze einen Dummy-Wert
            # (Dies sollte nicht nötig sein, aber als Fallback)
            pass
        except:
            pass
    finally:
        db.close()
    
    # Migration: Status "unqualifiziert" ist jetzt verfügbar
    # SQLite speichert Enums als String, daher funktioniert der neue Status automatisch
    print("[OK] Status 'unqualifiziert' ist jetzt verfuegbar")
    
    # Erstelle Admin-User "ben" falls nicht vorhanden
    db = SessionLocal()
    try:
        admin_user = get_user_by_username(db, "ben")
        if not admin_user:
            from .models.user import User
            import secrets
            import string
            
            # Generiere sicheres Standard-Passwort
            alphabet = string.ascii_letters + string.digits
            default_password = ''.join(secrets.choice(alphabet) for i in range(16))
            
            admin_user = User(
                username="ben",
                email="ben@example.com",  # Gültige E-Mail-Adresse (kein .local)
                hashed_password=get_password_hash(default_password),
                role=UserRole.ADMIN,
                is_active=True
            )
            db.add(admin_user)
            db.commit()
            print("=" * 80)
            print("⚠️  WICHTIG: Admin-User 'ben' wurde erstellt")
            print(f"   Standard-Passwort: {default_password}")
            print("   BITTE ÄNDERN SIE DAS PASSWORT NACH DEM ERSTEN LOGIN!")
            print("=" * 80)
        else:
            # Stelle sicher, dass "ben" immer Admin ist und gültige E-Mail hat
            if admin_user.role != UserRole.ADMIN:
                admin_user.role = UserRole.ADMIN
            if admin_user.email.endswith('.local') or '@admin.local' in admin_user.email:
                admin_user.email = 'ben@example.com'
            db.commit()
            print("User 'ben' wurde aktualisiert")
    finally:
        db.close()
    
    # Migration: Erstelle/aktualisiere chat_messages Tabelle
    db = SessionLocal()
    try:
        # Prüfe ob Tabelle existiert
        result = db.execute(text("SELECT name FROM sqlite_master WHERE type='table' AND name='chat_messages'"))
        table_exists = result.fetchone() is not None
        
        if not table_exists:
            print("Fuehre Migration aus: Erstelle chat_messages Tabelle...")
            db.execute(text("""
                CREATE TABLE chat_messages (
                    id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
                    from_user_id INTEGER,
                    from_makler_id INTEGER,
                    to_user_id INTEGER,
                    to_makler_id INTEGER,
                    nachricht VARCHAR NOT NULL,
                    erstellt_am DATETIME NOT NULL,
                    gelesen BOOLEAN NOT NULL DEFAULT 0,
                    FOREIGN KEY(from_user_id) REFERENCES users (id),
                    FOREIGN KEY(from_makler_id) REFERENCES makler (id),
                    FOREIGN KEY(to_user_id) REFERENCES users (id),
                    FOREIGN KEY(to_makler_id) REFERENCES makler (id)
                )
            """))
            db.execute(text("CREATE INDEX IF NOT EXISTS idx_chat_messages_from_user_id ON chat_messages(from_user_id)"))
            db.execute(text("CREATE INDEX IF NOT EXISTS idx_chat_messages_from_makler_id ON chat_messages(from_makler_id)"))
            db.execute(text("CREATE INDEX IF NOT EXISTS idx_chat_messages_to_user_id ON chat_messages(to_user_id)"))
            db.execute(text("CREATE INDEX IF NOT EXISTS idx_chat_messages_to_makler_id ON chat_messages(to_makler_id)"))
            # Performance-Indizes für häufige Queries
            db.execute(text("CREATE INDEX IF NOT EXISTS idx_chat_messages_erstellt_am ON chat_messages(erstellt_am)"))
            db.execute(text("CREATE INDEX IF NOT EXISTS idx_chat_messages_gelesen ON chat_messages(gelesen)"))
            # Composite Index für häufige WHERE-Klauseln
            db.execute(text("CREATE INDEX IF NOT EXISTS idx_chat_messages_to_user_gelesen ON chat_messages(to_user_id, gelesen)"))
            db.execute(text("CREATE INDEX IF NOT EXISTS idx_chat_messages_from_makler_gelesen ON chat_messages(from_makler_id, gelesen)"))
            db.commit()
            print("[OK] chat_messages Tabelle erfolgreich erstellt")
        else:
            # Migration: Alte Spalten zu neuen Spalten migrieren
            result = db.execute(text("PRAGMA table_info(chat_messages)"))
            columns = [row[1] for row in result.fetchall()]
            
            if 'from_user_id' not in columns:
                print("Fuehre Migration aus: Aktualisiere chat_messages Tabelle auf neues Format...")
                # Erstelle Backup
                db.execute(text("CREATE TABLE IF NOT EXISTS chat_messages_backup AS SELECT * FROM chat_messages"))
                
                # Lösche alte Tabelle
                db.execute(text("DROP TABLE IF EXISTS chat_messages"))
                
                # Erstelle neue Tabelle
                db.execute(text("""
                    CREATE TABLE chat_messages (
                        id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
                        from_user_id INTEGER,
                        from_makler_id INTEGER,
                        to_user_id INTEGER,
                        to_makler_id INTEGER,
                        nachricht VARCHAR NOT NULL,
                        erstellt_am DATETIME NOT NULL,
                        gelesen BOOLEAN NOT NULL DEFAULT 0,
                        FOREIGN KEY(from_user_id) REFERENCES users (id),
                        FOREIGN KEY(from_makler_id) REFERENCES makler (id),
                        FOREIGN KEY(to_user_id) REFERENCES users (id),
                        FOREIGN KEY(to_makler_id) REFERENCES makler (id)
                    )
                """))
                
                # Migriere Daten: Alte user_id/makler_id zu from_user_id/from_makler_id
                # to_user_id/to_makler_id bleiben NULL (alte Nachrichten waren Broadcast)
                db.execute(text("""
                    INSERT INTO chat_messages (id, from_user_id, from_makler_id, nachricht, erstellt_am, gelesen)
                    SELECT id, user_id, makler_id, nachricht, erstellt_am, gelesen
                    FROM chat_messages_backup
                """))
                
                # Erstelle Indizes
                db.execute(text("CREATE INDEX IF NOT EXISTS idx_chat_messages_from_user_id ON chat_messages(from_user_id)"))
                db.execute(text("CREATE INDEX IF NOT EXISTS idx_chat_messages_from_makler_id ON chat_messages(from_makler_id)"))
                db.execute(text("CREATE INDEX IF NOT EXISTS idx_chat_messages_to_user_id ON chat_messages(to_user_id)"))
                db.execute(text("CREATE INDEX IF NOT EXISTS idx_chat_messages_to_makler_id ON chat_messages(to_makler_id)"))
                # Performance-Indizes für häufige Queries
                db.execute(text("CREATE INDEX IF NOT EXISTS idx_chat_messages_erstellt_am ON chat_messages(erstellt_am)"))
                db.execute(text("CREATE INDEX IF NOT EXISTS idx_chat_messages_gelesen ON chat_messages(gelesen)"))
                # Composite Index für häufige WHERE-Klauseln
                db.execute(text("CREATE INDEX IF NOT EXISTS idx_chat_messages_to_user_gelesen ON chat_messages(to_user_id, gelesen)"))
                db.execute(text("CREATE INDEX IF NOT EXISTS idx_chat_messages_from_makler_gelesen ON chat_messages(from_makler_id, gelesen)"))
                
                # Lösche Backup
                db.execute(text("DROP TABLE IF EXISTS chat_messages_backup"))
                
                db.commit()
                print("[OK] chat_messages Tabelle erfolgreich migriert")
    except Exception as e:
        db.rollback()
        print(f"Warnung bei Migration (chat_messages): {e}")
    
    # Stelle sicher, dass alle Performance-Indizes existieren (auch für bestehende Tabellen)
    try:
        db.execute(text("CREATE INDEX IF NOT EXISTS idx_chat_messages_erstellt_am ON chat_messages(erstellt_am)"))
        db.execute(text("CREATE INDEX IF NOT EXISTS idx_chat_messages_gelesen ON chat_messages(gelesen)"))
        db.execute(text("CREATE INDEX IF NOT EXISTS idx_chat_messages_to_user_gelesen ON chat_messages(to_user_id, gelesen)"))
        db.execute(text("CREATE INDEX IF NOT EXISTS idx_chat_messages_from_makler_gelesen ON chat_messages(from_makler_id, gelesen)"))
        db.commit()
    except Exception as e:
        print(f"Warnung beim Erstellen von Performance-Indizes: {e}")
    finally:
        db.close()
    
    # Migration: Füge weitere Performance-Indizes hinzu
    db = SessionLocal()
    try:
        print("Erstelle Performance-Indizes...")
        
        # Leads-Indizes
        db.execute(text("CREATE INDEX IF NOT EXISTS idx_leads_makler_id ON leads(makler_id)"))
        db.execute(text("CREATE INDEX IF NOT EXISTS idx_leads_status ON leads(status)"))
        db.execute(text("CREATE INDEX IF NOT EXISTS idx_leads_makler_status ON leads(makler_id, status)"))
        db.execute(text("CREATE INDEX IF NOT EXISTS idx_leads_qualifiziert_am ON leads(qualifiziert_am)"))
        db.execute(text("CREATE INDEX IF NOT EXISTS idx_leads_erstellt_am ON leads(erstellt_am)"))
        db.execute(text("CREATE INDEX IF NOT EXISTS idx_leads_qualifiziert_von_user_id ON leads(qualifiziert_von_user_id)"))
        
        # Rechnungen-Indizes
        db.execute(text("CREATE INDEX IF NOT EXISTS idx_rechnungen_makler_id ON rechnungen(makler_id)"))
        db.execute(text("CREATE INDEX IF NOT EXISTS idx_rechnungen_status ON rechnungen(status)"))
        db.execute(text("CREATE INDEX IF NOT EXISTS idx_rechnungen_makler_status ON rechnungen(makler_id, status)"))
        db.execute(text("CREATE INDEX IF NOT EXISTS idx_rechnungen_jahr_monat ON rechnungen(jahr, monat)"))
        db.execute(text("CREATE INDEX IF NOT EXISTS idx_rechnungen_rechnungstyp ON rechnungen(rechnungstyp)"))
        db.execute(text("CREATE INDEX IF NOT EXISTS idx_rechnungen_lead_id ON rechnungen(lead_id)"))
        
        # Makler-Indizes
        db.execute(text("CREATE INDEX IF NOT EXISTS idx_makler_email ON makler(email)"))
        db.execute(text("CREATE INDEX IF NOT EXISTS idx_makler_vertrag_pausiert ON makler(vertrag_pausiert)"))
        
        # MaklerCredits-Indizes
        db.execute(text("CREATE INDEX IF NOT EXISTS idx_makler_credits_makler_id ON makler_credits(makler_id)"))
        db.execute(text("CREATE INDEX IF NOT EXISTS idx_makler_credits_erstellt_am ON makler_credits(erstellt_am)"))
        db.execute(text("CREATE INDEX IF NOT EXISTS idx_makler_credits_transaktionstyp ON makler_credits(transaktionstyp)"))
        
        # CreditsRueckzahlungAnfragen-Indizes
        db.execute(text("CREATE INDEX IF NOT EXISTS idx_credits_rueckzahlung_makler_id ON credits_rueckzahlung_anfragen(makler_id)"))
        db.execute(text("CREATE INDEX IF NOT EXISTS idx_credits_rueckzahlung_status ON credits_rueckzahlung_anfragen(status)"))
        
        db.commit()
        print("[OK] Performance-Indizes erfolgreich erstellt")
    except Exception as e:
        db.rollback()
        print(f"Warnung beim Erstellen von Performance-Indizes: {e}")
    finally:
        db.close()
    
    # Migration: Füge 'preis' Spalte zur leads-Tabelle hinzu falls sie nicht existiert
    db = SessionLocal()
    try:
        result = db.execute(text("PRAGMA table_info(leads)"))
        columns = [row[1] for row in result.fetchall()]
        
        if 'preis' not in columns:
            print("Fuehre Migration aus: Fuege 'preis' Spalte zur leads-Tabelle hinzu...")
            db.execute(text("ALTER TABLE leads ADD COLUMN preis REAL"))
            db.commit()
            print("[OK] 'preis' Spalte erfolgreich hinzugefuegt")
        else:
            print("[OK] 'preis' Spalte existiert bereits")
    except Exception as e:
        db.rollback()
        print(f"Warnung bei Migration (preis Spalte): {e}")
    finally:
        db.close()
    
    # Migration: Füge neue Lead-Felder (immobilien_typ, baujahr, lage) zur leads-Tabelle hinzu falls sie nicht existieren
    db = SessionLocal()
    try:
        result = db.execute(text("PRAGMA table_info(leads)"))
        columns = [row[1] for row in result.fetchall()]
        
        new_lead_columns = {
            'immobilien_typ': 'VARCHAR',
            'baujahr': 'INTEGER',
            'lage': 'VARCHAR'
        }
        
        added_columns = []
        for col_name, col_type in new_lead_columns.items():
            if col_name not in columns:
                print(f"Fuehre Migration aus: Fuege '{col_name}' Spalte zur leads-Tabelle hinzu...")
                db.execute(text(f"ALTER TABLE leads ADD COLUMN {col_name} {col_type}"))
                added_columns.append(col_name)
        
        if added_columns:
            db.commit()
            print(f"[OK] Neue Lead-Spalten erfolgreich hinzugefuegt: {', '.join(added_columns)}")
        else:
            print("[OK] Alle neuen Lead-Spalten existieren bereits")
    except Exception as e:
        db.rollback()
        print(f"Warnung bei Migration (neue Lead-Spalten): {e}")
    finally:
        db.close()
    
    # Migration: Füge Telefon-Kontakt-Felder zur leads-Tabelle hinzu falls sie nicht existieren
    db = SessionLocal()
    try:
        result = db.execute(text("PRAGMA table_info(leads)"))
        columns = [row[1] for row in result.fetchall()]
        
        telefon_kontakt_columns = {
            'telefon_kontakt_ergebnis': 'VARCHAR',
            'telefon_kontakt_datum': 'DATE',
            'telefon_kontakt_uhrzeit': 'VARCHAR'
        }
        
        added_columns = []
        for col_name, col_type in telefon_kontakt_columns.items():
            if col_name not in columns:
                print(f"Fuehre Migration aus: Fuege '{col_name}' Spalte zur leads-Tabelle hinzu...")
                db.execute(text(f"ALTER TABLE leads ADD COLUMN {col_name} {col_type}"))
                added_columns.append(col_name)
        
        if added_columns:
            db.commit()
            print(f"[OK] Telefon-Kontakt-Spalten erfolgreich hinzugefuegt: {', '.join(added_columns)}")
        else:
            print("[OK] Alle Telefon-Kontakt-Spalten existieren bereits")
    except Exception as e:
        db.rollback()
        print(f"Warnung bei Migration (Telefon-Kontakt-Spalten): {e}")
    finally:
        db.close()
    
    # Migration: Füge Locking-Felder zur leads-Tabelle hinzu falls sie nicht existieren
    db = SessionLocal()
    try:
        result = db.execute(text("PRAGMA table_info(leads)"))
        columns = [row[1] for row in result.fetchall()]
        
        locking_columns = {
            'bearbeitet_von_user_id': 'INTEGER',
            'bearbeitet_seit': 'DATETIME'
        }
        
        added_columns = []
        for col_name, col_type in locking_columns.items():
            if col_name not in columns:
                print(f"Fuehre Migration aus: Fuege '{col_name}' Spalte zur leads-Tabelle hinzu...")
                db.execute(text(f"ALTER TABLE leads ADD COLUMN {col_name} {col_type}"))
                added_columns.append(col_name)
        
        if added_columns:
            db.commit()
            print(f"[OK] Locking-Spalten erfolgreich hinzugefuegt: {', '.join(added_columns)}")
        else:
            print("[OK] Alle Locking-Spalten existieren bereits")
    except Exception as e:
        db.rollback()
        print(f"Warnung bei Migration (Locking-Spalten): {e}")
    finally:
        db.close()
    
    # Migration: Füge Checklisten-Felder zur leads-Tabelle hinzu falls sie nicht existieren
    db = SessionLocal()
    try:
        result = db.execute(text("PRAGMA table_info(leads)"))
        columns = [row[1] for row in result.fetchall()]
        
        checklisten_columns = {
            'termin_vereinbart': 'INTEGER DEFAULT 0',
            'termin_ort': 'VARCHAR',
            'termin_datum': 'DATE',
            'termin_uhrzeit': 'VARCHAR',
            'termin_notiz': 'TEXT',
            'absage': 'INTEGER DEFAULT 0',
            'absage_notiz': 'TEXT',
            'zweit_termin_vereinbart': 'INTEGER DEFAULT 0',
            'zweit_termin_ort': 'VARCHAR',
            'zweit_termin_datum': 'DATE',
            'zweit_termin_uhrzeit': 'VARCHAR',
            'zweit_termin_notiz': 'TEXT',
            'maklervertrag_unterschrieben': 'INTEGER DEFAULT 0',
            'maklervertrag_notiz': 'TEXT',
            'immobilie_verkauft': 'INTEGER DEFAULT 0',
            'immobilie_verkauft_datum': 'DATE',
            'immobilie_verkauft_preis': 'VARCHAR',
            'favorit': 'INTEGER DEFAULT 0',
            'makler_angesehen': 'INTEGER DEFAULT 0',
            'lead_nummer': 'INTEGER'
        }
        
        added_columns = []
        for col_name, col_def in checklisten_columns.items():
            if col_name not in columns:
                print(f"Fuehre Migration aus: Fuege '{col_name}' Spalte zur leads-Tabelle hinzu...")
                db.execute(text(f"ALTER TABLE leads ADD COLUMN {col_name} {col_def}"))
                added_columns.append(col_name)
        
        if added_columns:
            db.commit()
            print(f"[OK] Checklisten-Spalten erfolgreich hinzugefuegt: {', '.join(added_columns)}")
        else:
            print("[OK] Alle Checklisten-Spalten existieren bereits")
        
        # Migration: Füge lead_nummer hinzu und weise bestehenden Leads Nummern zu
        db = SessionLocal()
        try:
            result = db.execute(text("PRAGMA table_info(leads)"))
            columns = [row[1] for row in result.fetchall()]
            
            if 'lead_nummer' not in columns:
                print("Fuehre Migration aus: Fuege lead_nummer Spalte zur leads-Tabelle hinzu...")
                db.execute(text("ALTER TABLE leads ADD COLUMN lead_nummer INTEGER"))
                db.commit()
                
                # Weise bestehenden Leads zufällige, eindeutige Nummern zu
                import random
                result = db.execute(text("SELECT id FROM leads ORDER BY id"))
                lead_rows = result.fetchall()
                
                # Generiere zufällige Nummern für jeden Lead
                used_numbers = set()
                for index, row in enumerate(lead_rows):
                    # Generiere zufällige 5-stellige Nummer zwischen 10000 und 99999
                    max_attempts = 1000
                    nummer = None
                    for _ in range(max_attempts):
                        candidate = random.randint(10000, 99999)
                        if candidate not in used_numbers:
                            # Prüfe auch in der Datenbank (falls Migration mehrmals läuft)
                            check_result = db.execute(text("SELECT COUNT(*) FROM leads WHERE lead_nummer = :num"), {"num": candidate})
                            if check_result.scalar() == 0:
                                nummer = candidate
                                used_numbers.add(candidate)
                                break
                    
                    if nummer is None:
                        # Fallback: 6-stellige Nummer
                        for _ in range(max_attempts):
                            candidate = random.randint(100000, 999999)
                            if candidate not in used_numbers:
                                check_result = db.execute(text("SELECT COUNT(*) FROM leads WHERE lead_nummer = :num"), {"num": candidate})
                                if check_result.scalar() == 0:
                                    nummer = candidate
                                    used_numbers.add(candidate)
                                    break
                    
                    if nummer:
                        db.execute(text("UPDATE leads SET lead_nummer = :num WHERE id = :id"), 
                                  {"num": nummer, "id": row[0]})
                    else:
                        # Letzter Fallback: Timestamp + ID
                        import time
                        nummer = (int(time.time() * 100) + row[0]) % 1000000
                        while nummer in used_numbers:
                            nummer = (nummer + 1) % 1000000
                        used_numbers.add(nummer)
                        db.execute(text("UPDATE leads SET lead_nummer = :num WHERE id = :id"), 
                                  {"num": nummer, "id": row[0]})
                
                db.commit()
                print(f"[OK] lead_nummer Spalte erfolgreich hinzugefuegt und {len(lead_rows)} bestehenden Leads zufaellige Nummern zugewiesen")
            else:
                # Stelle sicher, dass alle Leads eine Nummer haben
                result = db.execute(text("SELECT COUNT(*) FROM leads WHERE lead_nummer IS NULL"))
                null_count = result.scalar()
                if null_count > 0:
                    # Hole alle existierenden Nummern
                    result = db.execute(text("SELECT lead_nummer FROM leads WHERE lead_nummer IS NOT NULL"))
                    existing_numbers = {row[0] for row in result.fetchall()}
                    
                    # Hole alle Leads ohne Nummer
                    result = db.execute(text("SELECT id FROM leads WHERE lead_nummer IS NULL ORDER BY id"))
                    null_lead_rows = result.fetchall()
                    
                    # Weise zufällige Nummern zu
                    import random
                    for row in null_lead_rows:
                        max_attempts = 1000
                        nummer = None
                        for _ in range(max_attempts):
                            candidate = random.randint(10000, 99999)
                            if candidate not in existing_numbers:
                                nummer = candidate
                                existing_numbers.add(candidate)
                                break
                        
                        if nummer is None:
                            # Fallback: 6-stellige Nummer
                            for _ in range(max_attempts):
                                candidate = random.randint(100000, 999999)
                                if candidate not in existing_numbers:
                                    nummer = candidate
                                    existing_numbers.add(candidate)
                                    break
                        
                        if nummer:
                            db.execute(text("UPDATE leads SET lead_nummer = :num WHERE id = :id"), 
                                      {"num": nummer, "id": row[0]})
                        else:
                            # Letzter Fallback: Timestamp + ID
                            import time
                            nummer = (int(time.time() * 100) + row[0]) % 1000000
                            while nummer in existing_numbers:
                                nummer = (nummer + 1) % 1000000
                            existing_numbers.add(nummer)
                            db.execute(text("UPDATE leads SET lead_nummer = :num WHERE id = :id"), 
                                      {"num": nummer, "id": row[0]})
                    
                    db.commit()
                    print(f"[OK] {len(null_lead_rows)} Leads wurde(n) eine zufaellige lead_nummer zugewiesen")
        except Exception as e:
            db.rollback()
            print(f"Warnung bei Migration (lead_nummer): {e}")
        finally:
            db.close()
    except Exception as e:
        db.rollback()
        print(f"Warnung bei Migration (Checklisten-Spalten): {e}")
    finally:
        db.close()
    
    # Migration: Füge beteiligungs_prozent zur leads-Tabelle hinzu
    db = SessionLocal()
    try:
        result = db.execute(text("PRAGMA table_info(leads)"))
        columns = [row[1] for row in result.fetchall()]
        
        if 'beteiligungs_prozent' not in columns:
            print("Fuehre Migration aus: Fuege beteiligungs_prozent Spalte zur leads-Tabelle hinzu...")
            db.execute(text("ALTER TABLE leads ADD COLUMN beteiligungs_prozent REAL"))
            db.commit()
            print("[OK] beteiligungs_prozent Spalte erfolgreich hinzugefuegt")
    except Exception as e:
        db.rollback()
        print(f"Warnung bei Migration (beteiligungs_prozent): {e}")
    finally:
        db.close()
    
    # Migration: Erweitere rechnungen-Tabelle für Beteiligungsabrechnungen
    db = SessionLocal()
    try:
        result = db.execute(text("PRAGMA table_info(rechnungen)"))
        columns_info = result.fetchall()
        columns = [row[1] for row in columns_info]
        
        # Prüfe ob monat/jahr Spalten NOT NULL sind (SQLite gibt 0 für NOT NULL zurück)
        monat_not_null = False
        jahr_not_null = False
        anzahl_leads_not_null = False
        preis_pro_lead_not_null = False
        
        for col_info in columns_info:
            col_name = col_info[1]
            col_notnull = col_info[3]  # 0 = nullable, 1 = NOT NULL
            if col_name == 'monat' and col_notnull == 1:
                monat_not_null = True
            elif col_name == 'jahr' and col_notnull == 1:
                jahr_not_null = True
            elif col_name == 'anzahl_leads' and col_notnull == 1:
                anzahl_leads_not_null = True
            elif col_name == 'preis_pro_lead' and col_notnull == 1:
                preis_pro_lead_not_null = True
        
        # Wenn monat/jahr/anzahl_leads/preis_pro_lead NOT NULL sind, muss die Tabelle neu erstellt werden
        needs_recreate = monat_not_null or jahr_not_null or anzahl_leads_not_null or preis_pro_lead_not_null
        
        if needs_recreate:
            print("Fuehre Migration aus: Erstelle rechnungen-Tabelle neu mit nullable Spalten...")
            
            # Erstelle Backup-Tabelle mit Daten
            db.execute(text("CREATE TABLE IF NOT EXISTS rechnungen_backup AS SELECT * FROM rechnungen"))
            
            # Erstelle neue Tabelle mit korrekten Constraints
            db.execute(text("DROP TABLE rechnungen"))
            db.execute(text("""
                CREATE TABLE rechnungen (
                    id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
                    makler_id INTEGER NOT NULL,
                    rechnungstyp VARCHAR NOT NULL DEFAULT 'monatlich',
                    monat INTEGER,
                    jahr INTEGER,
                    anzahl_leads INTEGER,
                    preis_pro_lead REAL,
                    lead_id INTEGER,
                    verkaufspreis REAL,
                    beteiligungs_prozent REAL,
                    netto_betrag REAL,
                    gesamtbetrag REAL NOT NULL,
                    erstellt_am DATETIME NOT NULL,
                    status VARCHAR NOT NULL DEFAULT 'offen',
                    created_by_user_id INTEGER,
                    FOREIGN KEY(makler_id) REFERENCES makler (id),
                    FOREIGN KEY(lead_id) REFERENCES leads (id),
                    FOREIGN KEY(created_by_user_id) REFERENCES users (id)
                )
            """))
            
            # Erstelle Indizes
            db.execute(text("CREATE INDEX IF NOT EXISTS ix_rechnungen_makler_id ON rechnungen(makler_id)"))
            db.execute(text("CREATE INDEX IF NOT EXISTS ix_rechnungen_lead_id ON rechnungen(lead_id)"))
            
            # Kopiere Daten zurück
            db.execute(text("""
                INSERT INTO rechnungen 
                (id, makler_id, rechnungstyp, monat, jahr, anzahl_leads, preis_pro_lead, 
                 lead_id, verkaufspreis, beteiligungs_prozent, netto_betrag, 
                 gesamtbetrag, erstellt_am, status, created_by_user_id)
                SELECT 
                    id, makler_id, 
                    COALESCE(rechnungstyp, 'monatlich'), 
                    monat, jahr, anzahl_leads, preis_pro_lead,
                    lead_id, verkaufspreis, beteiligungs_prozent, netto_betrag,
                    gesamtbetrag, erstellt_am, COALESCE(status, 'offen'), created_by_user_id
                FROM rechnungen_backup
            """))
            
            # Lösche Backup
            db.execute(text("DROP TABLE rechnungen_backup"))
            
            db.commit()
            print("[OK] rechnungen-Tabelle erfolgreich neu erstellt mit nullable Spalten")
        else:
            # Normale Migration: Füge nur neue Spalten hinzu
            new_columns = {
                'rechnungstyp': ("VARCHAR DEFAULT 'monatlich'", "UPDATE rechnungen SET rechnungstyp = 'monatlich' WHERE rechnungstyp IS NULL"),
                'lead_id': ("INTEGER", None),
                'verkaufspreis': ("REAL", None),
                'beteiligungs_prozent': ("REAL", None),
                'netto_betrag': ("REAL", None)
            }
            
            added_columns = []
            for col_name, (col_def, update_sql) in new_columns.items():
                if col_name not in columns:
                    db.execute(text(f"ALTER TABLE rechnungen ADD COLUMN {col_name} {col_def}"))
                    added_columns.append(col_name)
                    if update_sql:
                        db.execute(text(update_sql))
            
            if added_columns:
                db.commit()
                print(f"[OK] Rechnung-Spalten erfolgreich hinzugefuegt: {', '.join(added_columns)}")
            else:
                print("[OK] Alle Rechnung-Spalten existieren bereits")
    except Exception as e:
        db.rollback()
        print(f"Warnung bei Migration (rechnungen Spalten): {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()
    
    # Migration: Füge status-Spalte zur rechnungen-Tabelle hinzu
    db = SessionLocal()
    try:
        result = db.execute(text("PRAGMA table_info(rechnungen)"))
        columns = [row[1] for row in result.fetchall()]
        
        if 'status' not in columns:
            print("Fuehre Migration aus: Fuege 'status' Spalte zur rechnungen-Tabelle hinzu...")
            db.execute(text("ALTER TABLE rechnungen ADD COLUMN status VARCHAR DEFAULT 'offen'"))
            # Setze bestehende Rechnungen auf 'offen'
            db.execute(text("UPDATE rechnungen SET status = 'offen' WHERE status IS NULL"))
            db.commit()
            print("[OK] 'status' Spalte erfolgreich zur rechnungen-Tabelle hinzugefuegt")
        else:
            print("[OK] 'status' Spalte existiert bereits")
    except Exception as e:
        db.rollback()
        print(f"Warnung bei Migration (rechnungen status Spalte): {e}")
    finally:
        db.close()
    
    # Migration: Füge Vertragsverwaltungs-Spalten zur makler-Tabelle hinzu
    db = SessionLocal()
    try:
        result = db.execute(text("PRAGMA table_info(makler)"))
        columns = [row[1] for row in result.fetchall()]
        
        # Neues Boolean-Feld für Vertragspause (einfacher On/Off)
        if 'vertrag_pausiert' not in columns:
            print("Fuehre Migration aus: Fuege 'vertrag_pausiert' Spalte zur makler-Tabelle hinzu...")
            db.execute(text("ALTER TABLE makler ADD COLUMN vertrag_pausiert INTEGER DEFAULT 0"))
            db.commit()
            print("[OK] vertrag_pausiert Spalte erfolgreich hinzugefuegt")
        else:
            print("[OK] vertrag_pausiert Spalte existiert bereits")
        
        # Vertrag bis (falls nicht vorhanden)
        if 'vertrag_bis' not in columns:
            print("Fuehre Migration aus: Fuege 'vertrag_bis' Spalte zur makler-Tabelle hinzu...")
            db.execute(text("ALTER TABLE makler ADD COLUMN vertrag_bis DATE"))
            db.commit()
            print("[OK] vertrag_bis Spalte erfolgreich hinzugefuegt")
        else:
            print("[OK] vertrag_bis Spalte existiert bereits")
            
        # Alte Spalten vertrag_pausiert_monat/jahr werden nicht mehr verwendet, aber bleiben in der DB
        # (für Rückwärtskompatibilität, werden aber nicht mehr genutzt)
    except Exception as e:
        db.rollback()
        print(f"Warnung bei Migration (makler Vertragsverwaltungs-Spalten): {e}")
    finally:
        db.close()
    
    # Migration: Füge Credits-System-Spalten zur makler-Tabelle hinzu
    db = SessionLocal()
    try:
        result = db.execute(text("PRAGMA table_info(makler)"))
        columns = [row[1] for row in result.fetchall()]
        
        credits_system_columns = {
            'rechnungssystem_typ': ("VARCHAR DEFAULT 'alt'", "UPDATE makler SET rechnungssystem_typ = 'alt' WHERE rechnungssystem_typ IS NULL"),
            'erste_leads_anzahl': ("INTEGER DEFAULT 5", None),
            'erste_leads_preis': ("REAL DEFAULT 50.0", None),
            'erste_leads_danach_preis': ("REAL DEFAULT 75.0", None),
            'automatische_aufladung_aktiv': ("INTEGER DEFAULT 0", None),
            'automatische_aufladung_betrag': ("REAL", None),
            'automatische_aufladung_tag': ("INTEGER", None)
        }
        
        added_columns = []
        for col_name, (col_def, update_sql) in credits_system_columns.items():
            if col_name not in columns:
                print(f"Fuehre Migration aus: Fuege '{col_name}' Spalte zur makler-Tabelle hinzu...")
                db.execute(text(f"ALTER TABLE makler ADD COLUMN {col_name} {col_def}"))
                added_columns.append(col_name)
                if update_sql:
                    db.execute(text(update_sql))
        
        if added_columns:
            db.commit()
            print(f"[OK] Credits-System-Spalten erfolgreich hinzugefuegt: {', '.join(added_columns)}")
        else:
            print("[OK] Alle Credits-System-Spalten existieren bereits")
    except Exception as e:
        db.rollback()
        print(f"Warnung bei Migration (makler Credits-System-Spalten): {e}")
    finally:
        db.close()
    
    # Migration: Erstelle makler_credits Tabelle
    db = SessionLocal()
    try:
        result = db.execute(text("SELECT name FROM sqlite_master WHERE type='table' AND name='makler_credits'"))
        table_exists = result.fetchone() is not None
        
        if not table_exists:
            print("Fuehre Migration aus: Erstelle makler_credits Tabelle...")
            db.execute(text("""
                CREATE TABLE makler_credits (
                    id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
                    makler_id INTEGER NOT NULL,
                    betrag REAL NOT NULL,
                    transaktionstyp VARCHAR NOT NULL DEFAULT 'aufladung',
                    lead_id INTEGER,
                    beschreibung TEXT,
                    erstellt_am DATETIME NOT NULL,
                    erstellt_von_user_id INTEGER,
                    zahlungsreferenz VARCHAR,
                    zahlungsstatus VARCHAR,
                    FOREIGN KEY(makler_id) REFERENCES makler (id),
                    FOREIGN KEY(lead_id) REFERENCES leads (id),
                    FOREIGN KEY(erstellt_von_user_id) REFERENCES users (id)
                )
            """))
            db.execute(text("CREATE INDEX IF NOT EXISTS ix_makler_credits_makler_id ON makler_credits(makler_id)"))
            db.execute(text("CREATE INDEX IF NOT EXISTS ix_makler_credits_lead_id ON makler_credits(lead_id)"))
            db.execute(text("CREATE INDEX IF NOT EXISTS ix_makler_credits_erstellt_am ON makler_credits(erstellt_am)"))
            db.commit()
            print("[OK] makler_credits Tabelle erfolgreich erstellt")
        else:
            print("[OK] makler_credits Tabelle existiert bereits")
            # Migration: Füge fehlende Spalten hinzu
            result = db.execute(text("PRAGMA table_info(makler_credits)"))
            columns = [row[1] for row in result.fetchall()]
            if 'zahlungsreferenz' not in columns:
                print("Fuehre Migration aus: Fuege zahlungsreferenz zur makler_credits-Tabelle hinzu...")
                db.execute(text("ALTER TABLE makler_credits ADD COLUMN zahlungsreferenz VARCHAR"))
                db.commit()
                print("[OK] zahlungsreferenz Spalte erfolgreich hinzugefuegt")
            if 'zahlungsstatus' not in columns:
                print("Fuehre Migration aus: Fuege zahlungsstatus zur makler_credits-Tabelle hinzu...")
                db.execute(text("ALTER TABLE makler_credits ADD COLUMN zahlungsstatus VARCHAR"))
                db.commit()
                print("[OK] zahlungsstatus Spalte erfolgreich hinzugefuegt")
    except Exception as e:
        db.rollback()
        print(f"Warnung bei Migration (makler_credits Tabelle): {e}")
    finally:
        db.close()
    
    # Migration: Erstelle credits_rueckzahlung_anfragen Tabelle
    db = SessionLocal()
    try:
        result = db.execute(text("SELECT name FROM sqlite_master WHERE type='table' AND name='credits_rueckzahlung_anfragen'"))
        table_exists = result.fetchone() is not None
        
        if not table_exists:
            print("Fuehre Migration aus: Erstelle credits_rueckzahlung_anfragen Tabelle...")
            db.execute(text("""
                CREATE TABLE credits_rueckzahlung_anfragen (
                    id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
                    makler_id INTEGER NOT NULL,
                    transaktion_id INTEGER NOT NULL,
                    betrag REAL NOT NULL,
                    status VARCHAR NOT NULL DEFAULT 'pending',
                    beschreibung TEXT,
                    erstellt_am DATETIME NOT NULL,
                    bearbeitet_am DATETIME,
                    bearbeitet_von_user_id INTEGER,
                    rueckzahlung_transaktion_id INTEGER,
                    FOREIGN KEY(makler_id) REFERENCES makler (id),
                    FOREIGN KEY(transaktion_id) REFERENCES makler_credits (id),
                    FOREIGN KEY(bearbeitet_von_user_id) REFERENCES users (id),
                    FOREIGN KEY(rueckzahlung_transaktion_id) REFERENCES makler_credits (id)
                )
            """))
            db.execute(text("CREATE INDEX IF NOT EXISTS ix_credits_rueckzahlung_anfragen_makler_id ON credits_rueckzahlung_anfragen(makler_id)"))
            db.execute(text("CREATE INDEX IF NOT EXISTS ix_credits_rueckzahlung_anfragen_status ON credits_rueckzahlung_anfragen(status)"))
            db.commit()
            print("[OK] credits_rueckzahlung_anfragen Tabelle erfolgreich erstellt")
        else:
            print("[OK] credits_rueckzahlung_anfragen Tabelle existiert bereits")
            # Migration: Füge neue Spalten hinzu
            result = db.execute(text("PRAGMA table_info(credits_rueckzahlung_anfragen)"))
            columns = [row[1] for row in result.fetchall()]
            if 'rueckzahlung_status' not in columns:
                print("Fuehre Migration aus: Fuege rueckzahlung_status zur credits_rueckzahlung_anfragen-Tabelle hinzu...")
                db.execute(text("ALTER TABLE credits_rueckzahlung_anfragen ADD COLUMN rueckzahlung_status VARCHAR"))
                db.commit()
                print("[OK] rueckzahlung_status Spalte erfolgreich hinzugefuegt")
            if 'stripe_refund_id' not in columns:
                print("Fuehre Migration aus: Fuege stripe_refund_id zur credits_rueckzahlung_anfragen-Tabelle hinzu...")
                db.execute(text("ALTER TABLE credits_rueckzahlung_anfragen ADD COLUMN stripe_refund_id VARCHAR"))
                db.commit()
                print("[OK] stripe_refund_id Spalte erfolgreich hinzugefuegt")
    except Exception as e:
        db.rollback()
        print(f"Warnung bei Migration (credits_rueckzahlung_anfragen): {e}")
    finally:
        db.close()
    
    # Migration: Füge chat_gruppe_id zur chat_messages-Tabelle hinzu
    db = SessionLocal()
    try:
        result = db.execute(text("PRAGMA table_info(chat_messages)"))
        columns = [row[1] for row in result.fetchall()]
        
        if 'chat_gruppe_id' not in columns:
            print("Fuehre Migration aus: Fuege chat_gruppe_id zur chat_messages-Tabelle hinzu...")
            db.execute(text("ALTER TABLE chat_messages ADD COLUMN chat_gruppe_id INTEGER"))
            db.execute(text("CREATE INDEX IF NOT EXISTS idx_chat_messages_chat_gruppe_id ON chat_messages(chat_gruppe_id)"))
            db.commit()
            print("[OK] chat_gruppe_id Spalte erfolgreich zur chat_messages-Tabelle hinzugefuegt")
        else:
            print("[OK] chat_gruppe_id Spalte existiert bereits in chat_messages")
    except Exception as e:
        db.rollback()
        print(f"Warnung bei Migration (chat_messages chat_gruppe_id): {e}")
    finally:
        db.close()
    
    # Migration: Erstelle chat_gruppen Tabelle
    db = SessionLocal()
    try:
        result = db.execute(text("SELECT name FROM sqlite_master WHERE type='table' AND name='chat_gruppen'"))
        table_exists = result.fetchone() is not None
        
        if not table_exists:
            print("Fuehre Migration aus: Erstelle chat_gruppen Tabelle...")
            db.execute(text("""
                CREATE TABLE chat_gruppen (
                    id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
                    name VARCHAR NOT NULL,
                    beschreibung VARCHAR,
                    erstellt_von_user_id INTEGER NOT NULL,
                    erstellt_am DATETIME NOT NULL,
                    FOREIGN KEY(erstellt_von_user_id) REFERENCES users (id)
                )
            """))
            db.execute(text("CREATE INDEX IF NOT EXISTS idx_chat_gruppen_erstellt_von_user_id ON chat_gruppen(erstellt_von_user_id)"))
            db.commit()
            print("[OK] chat_gruppen Tabelle erfolgreich erstellt")
        else:
            print("[OK] chat_gruppen Tabelle existiert bereits")
    except Exception as e:
        db.rollback()
        print(f"Warnung bei Migration (chat_gruppen Tabelle): {e}")
    finally:
        db.close()
    
    # Migration: Erstelle chat_gruppe_teilnehmer Tabelle
    db = SessionLocal()
    try:
        result = db.execute(text("SELECT name FROM sqlite_master WHERE type='table' AND name='chat_gruppe_teilnehmer'"))
        table_exists = result.fetchone() is not None
        
        if not table_exists:
            print("Fuehre Migration aus: Erstelle chat_gruppe_teilnehmer Tabelle...")
            db.execute(text("""
                CREATE TABLE chat_gruppe_teilnehmer (
                    chat_gruppe_id INTEGER NOT NULL,
                    user_id INTEGER NOT NULL,
                    PRIMARY KEY (chat_gruppe_id, user_id),
                    FOREIGN KEY(chat_gruppe_id) REFERENCES chat_gruppen (id),
                    FOREIGN KEY(user_id) REFERENCES users (id)
                )
            """))
            db.execute(text("CREATE INDEX IF NOT EXISTS idx_chat_gruppe_teilnehmer_chat_gruppe_id ON chat_gruppe_teilnehmer(chat_gruppe_id)"))
            db.execute(text("CREATE INDEX IF NOT EXISTS idx_chat_gruppe_teilnehmer_user_id ON chat_gruppe_teilnehmer(user_id)"))
            db.commit()
            print("[OK] chat_gruppe_teilnehmer Tabelle erfolgreich erstellt")
        else:
            print("[OK] chat_gruppe_teilnehmer Tabelle existiert bereits")
    except Exception as e:
        db.rollback()
        print(f"Warnung bei Migration (chat_gruppe_teilnehmer Tabelle): {e}")
    finally:
        db.close()
    
    # Migration: Erstelle tickets Tabelle
    db = SessionLocal()
    try:
        result = db.execute(text("SELECT name FROM sqlite_master WHERE type='table' AND name='tickets'"))
        table_exists = result.fetchone() is not None
        
        if not table_exists:
            print("Fuehre Migration aus: Erstelle tickets Tabelle...")
            db.execute(text("""
                CREATE TABLE tickets (
                    id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
                    titel VARCHAR,
                    beschreibung VARCHAR NOT NULL,
                    faelligkeitsdatum DATE,
                    dringlichkeit VARCHAR NOT NULL DEFAULT 'mittel',
                    erstellt_von_user_id INTEGER NOT NULL,
                    chat_gruppe_id INTEGER,
                    erstellt_am DATETIME NOT NULL,
                    aktualisiert_am DATETIME NOT NULL,
                    geschlossen INTEGER NOT NULL DEFAULT 0,
                    FOREIGN KEY(erstellt_von_user_id) REFERENCES users (id),
                    FOREIGN KEY(chat_gruppe_id) REFERENCES chat_gruppen (id)
                )
            """))
            db.execute(text("CREATE INDEX IF NOT EXISTS idx_tickets_erstellt_von_user_id ON tickets(erstellt_von_user_id)"))
            db.execute(text("CREATE INDEX IF NOT EXISTS idx_tickets_chat_gruppe_id ON tickets(chat_gruppe_id)"))
            db.execute(text("CREATE INDEX IF NOT EXISTS idx_tickets_geschlossen ON tickets(geschlossen)"))
            db.commit()
            print("[OK] tickets Tabelle erfolgreich erstellt")
        else:
            print("[OK] tickets Tabelle existiert bereits")
            # Migration: Füge fehlende Spalten hinzu
            result = db.execute(text("PRAGMA table_info(tickets)"))
            columns = [row[1] for row in result.fetchall()]
            if 'chat_gruppe_id' not in columns:
                print("Fuehre Migration aus: Fuege chat_gruppe_id zur tickets-Tabelle hinzu...")
                db.execute(text("ALTER TABLE tickets ADD COLUMN chat_gruppe_id INTEGER"))
                db.execute(text("CREATE INDEX IF NOT EXISTS idx_tickets_chat_gruppe_id ON tickets(chat_gruppe_id)"))
                db.commit()
                print("[OK] chat_gruppe_id Spalte erfolgreich zur tickets-Tabelle hinzugefuegt")
            if 'titel' not in columns:
                print("Fuehre Migration aus: Fuege titel zur tickets-Tabelle hinzu...")
                db.execute(text("ALTER TABLE tickets ADD COLUMN titel VARCHAR"))
                db.commit()
                print("[OK] titel Spalte erfolgreich zur tickets-Tabelle hinzugefuegt")
    except Exception as e:
        db.rollback()
        print(f"Warnung bei Migration (tickets Tabelle): {e}")
    finally:
        db.close()
    
    # Migration: Erstelle ticket_teilnehmer Tabelle
    db = SessionLocal()
    try:
        result = db.execute(text("SELECT name FROM sqlite_master WHERE type='table' AND name='ticket_teilnehmer'"))
        table_exists = result.fetchone() is not None
        
        if not table_exists:
            print("Fuehre Migration aus: Erstelle ticket_teilnehmer Tabelle...")
            db.execute(text("""
                CREATE TABLE ticket_teilnehmer (
                    ticket_id INTEGER NOT NULL,
                    user_id INTEGER NOT NULL,
                    PRIMARY KEY (ticket_id, user_id),
                    FOREIGN KEY(ticket_id) REFERENCES tickets (id),
                    FOREIGN KEY(user_id) REFERENCES users (id)
                )
            """))
            db.execute(text("CREATE INDEX IF NOT EXISTS idx_ticket_teilnehmer_ticket_id ON ticket_teilnehmer(ticket_id)"))
            db.execute(text("CREATE INDEX IF NOT EXISTS idx_ticket_teilnehmer_user_id ON ticket_teilnehmer(user_id)"))
            db.commit()
            print("[OK] ticket_teilnehmer Tabelle erfolgreich erstellt")
        else:
            print("[OK] ticket_teilnehmer Tabelle existiert bereits")
    except Exception as e:
        db.rollback()
        print(f"Warnung bei Migration (ticket_teilnehmer Tabelle): {e}")
    finally:
        db.close()


