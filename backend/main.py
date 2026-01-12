from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
import os

from .routers import makler, leads, rechnungen, statistiken, export, makler_stats, makler_monatsstatistik, auth, upload, gatelink, credits, stripe, organisation, tickets
from .database import init_db
from .config import ALLOWED_ORIGINS, ENVIRONMENT, RATE_LIMIT_ENABLED, RATE_LIMIT_PER_MINUTE


def create_app() -> FastAPI:
    """
    Erzeugt die FastAPI-Anwendung und registriert alle Router.
    """
    # Datenbank initialisieren
    init_db()
    
    app = FastAPI(title="LeadGate CRM & Abrechnung")
    
    # CORS-Middleware hinzufügen
    app.add_middleware(
        CORSMiddleware,
        allow_origins=ALLOWED_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Rate Limiting hinzufügen
    if RATE_LIMIT_ENABLED:
        try:
            from slowapi import Limiter, _rate_limit_exceeded_handler
            from slowapi.util import get_remote_address
            from slowapi.errors import RateLimitExceeded
            
            limiter = Limiter(key_func=get_remote_address)
            app.state.limiter = limiter
            app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
        except ImportError:
            import warnings
            warnings.warn("slowapi nicht installiert. Rate Limiting deaktiviert. Installiere mit: pip install slowapi")
    
    # Exception Handler für bessere Fehlerbehandlung
    from fastapi.exceptions import RequestValidationError
    from fastapi.responses import JSONResponse
    from .logging_config import get_logger
    
    logger = get_logger("main")
    
    @app.exception_handler(Exception)
    async def global_exception_handler(request, exc):
        import traceback
        error_detail = str(exc)
        traceback_str = traceback.format_exc()
        
        # Logge den Fehler
        logger.error(f"Unhandled exception: {error_detail}", exc_info=True)
        
        # In Produktion keine internen Details preisgeben
        if ENVIRONMENT == "production":
            return JSONResponse(
                status_code=500,
                content={"detail": "Internal Server Error"}
            )
        else:
            # In Entwicklung: Zeige Details
            return JSONResponse(
                status_code=500,
                content={"detail": f"Internal Server Error: {error_detail}"}
            )

    # Health-Check Endpoint
    @app.get("/health")
    async def health_check():
        """Health-Check Endpoint für Monitoring."""
        try:
            # Prüfe Datenbank-Verbindung
            from .database import SessionLocal
            from sqlalchemy import text
            db = SessionLocal()
            db.execute(text("SELECT 1"))
            db.close()
            return {
                "status": "healthy",
                "database": "connected",
                "environment": ENVIRONMENT
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "database": "disconnected",
                "error": str(e) if ENVIRONMENT != "production" else "Database error"
            }
    
    # Test-Route
    @app.get("/test")
    async def test():
        return {"status": "ok", "message": "Server läuft"}

    # Router registrieren
    app.include_router(auth.router, prefix="/api/auth", tags=["Authentifizierung"])
    app.include_router(makler.router, prefix="/api/makler", tags=["Makler"])
    app.include_router(leads.router, prefix="/api/leads", tags=["Leads"])
    app.include_router(tickets.router, prefix="/api", tags=["Tickets"])
    app.include_router(
        rechnungen.router, prefix="/api/rechnungen", tags=["Rechnungen"]
    )
    app.include_router(
        statistiken.router, prefix="/api/statistiken", tags=["Statistiken"]
    )
    app.include_router(
        export.router, prefix="/api/export", tags=["Export"]
    )
    # Separate Prefix für Makler-Statistik-Endpunkte, damit sie nicht mit /api/makler/{makler_id} kollidieren
    app.include_router(
        makler_stats.router, prefix="/api/makler-stats", tags=["Makler-Statistiken"]
    )
    app.include_router(
        makler_monatsstatistik.router, prefix="/api/makler-stats", tags=["Makler-Statistiken"]
    )
    app.include_router(
        upload.router, prefix="/api", tags=["Upload"]
    )
    app.include_router(
        gatelink.router, prefix="/api/gatelink", tags=["GateLink"]
    )
    app.include_router(
        credits.router, prefix="/api", tags=["Credits"]
    )
    app.include_router(
        stripe.router, prefix="/api", tags=["Stripe"]
    )
    app.include_router(
        organisation.router, prefix="/api", tags=["Organisation"]
    )

    # Frontend-Pfad bestimmen
    backend_dir = os.path.dirname(__file__)  # backend/
    project_dir = os.path.dirname(backend_dir)  # Projekt-Root
    frontend_path = os.path.join(project_dir, "frontend")
    
    # Frontend-Routen ZUERST registrieren (vor StaticFiles-Mount)
    @app.get("/")
    async def read_root():
        login_path = os.path.join(frontend_path, "login.html")
        if os.path.exists(login_path):
            return FileResponse(login_path, media_type="text/html")
        return {"message": "LeadGate CRM & Abrechnung API", "error": "login.html not found", "frontend_path": str(frontend_path)}
    
    @app.get("/makler.html")
    async def makler_page():
        path = os.path.join(frontend_path, "makler.html")
        if os.path.exists(path):
            # Cache-Control Header setzen, um Browser-Caching zu verhindern
            from fastapi.responses import Response
            with open(path, 'rb') as f:
                content = f.read()
            return Response(
                content=content,
                media_type="text/html",
                headers={
                    "Cache-Control": "no-cache, no-store, must-revalidate",
                    "Pragma": "no-cache",
                    "Expires": "0"
                }
            )
        raise HTTPException(status_code=404)

    @app.get("/leads.html")
    async def leads_page():
        path = os.path.join(frontend_path, "leads.html")
        if os.path.exists(path):
            return FileResponse(path, media_type="text/html")
        raise HTTPException(status_code=404)

    @app.get("/abrechnung.html")
    async def abrechnung_page():
        path = os.path.join(frontend_path, "abrechnung.html")
        if os.path.exists(path):
            return FileResponse(path, media_type="text/html")
        raise HTTPException(status_code=404)

    @app.get("/index.html")
    async def index_page():
        path = os.path.join(frontend_path, "index.html")
        if os.path.exists(path):
            return FileResponse(path, media_type="text/html")
        raise HTTPException(status_code=404)

    @app.get("/login.html")
    async def login_page():
        path = os.path.join(frontend_path, "login.html")
        if os.path.exists(path):
            return FileResponse(path, media_type="text/html")
        raise HTTPException(status_code=404)

    @app.get("/test.html")
    async def test_page():
        path = os.path.join(frontend_path, "test.html")
        if os.path.exists(path):
            return FileResponse(path, media_type="text/html")
        raise HTTPException(status_code=404)

    @app.get("/test_login.html")
    async def test_login_page():
        path = os.path.join(frontend_path, "test_login.html")
        if os.path.exists(path):
            return FileResponse(path, media_type="text/html")
        raise HTTPException(status_code=404)

    @app.get("/benutzer.html")
    async def benutzer_page():
        path = os.path.join(frontend_path, "benutzer.html")
        print(f"DEBUG: benutzer.html route called, path: {path}, exists: {os.path.exists(path)}")
        if os.path.exists(path):
            return FileResponse(path, media_type="text/html")
        print(f"DEBUG: benutzer.html not found at {path}")
        raise HTTPException(status_code=404, detail=f"benutzer.html not found at {path}")

    @app.get("/benutzer")
    async def benutzer_page_redirect():
        path = os.path.join(frontend_path, "benutzer.html")
        if os.path.exists(path):
            return FileResponse(path, media_type="text/html")
        raise HTTPException(status_code=404)

    @app.get("/upload.html")
    async def upload_page():
        path = os.path.join(frontend_path, "upload.html")
        if os.path.exists(path):
            return FileResponse(path, media_type="text/html")
        raise HTTPException(status_code=404)
    
    @app.get("/rueckzahlungen.html")
    async def rueckzahlungen_page():
        path = os.path.join(frontend_path, "rueckzahlungen.html")
        if os.path.exists(path):
            return FileResponse(path, media_type="text/html")
        raise HTTPException(status_code=404, detail=f"rueckzahlungen.html not found at {path}")
    
    @app.get("/finanzen.html")
    async def finanzen_page():
        path = os.path.join(frontend_path, "finanzen.html")
        if os.path.exists(path):
            return FileResponse(path, media_type="text/html")
        raise HTTPException(status_code=404, detail=f"finanzen.html not found at {path}")
    
    @app.get("/gatelink")
    async def gatelink_login_page():
        path = os.path.join(frontend_path, "gatelink_login.html")
        if os.path.exists(path):
            return FileResponse(path, media_type="text/html")
        raise HTTPException(status_code=404)
    
    @app.get("/gatelink.html")
    async def gatelink_login_page_alt():
        path = os.path.join(frontend_path, "gatelink_login.html")
        if os.path.exists(path):
            return FileResponse(path, media_type="text/html")
        raise HTTPException(status_code=404)
    
    @app.get("/gatelink/dashboard")
    async def gatelink_dashboard_page():
        path = os.path.join(frontend_path, "gatelink_dashboard.html")
        if os.path.exists(path):
            return FileResponse(path, media_type="text/html")
        raise HTTPException(status_code=404)
    
    # Static-Files NACH den Routen mounten
    if os.path.exists(frontend_path):
        app.mount("/static", StaticFiles(directory=frontend_path), name="static")

    return app


app = create_app()
