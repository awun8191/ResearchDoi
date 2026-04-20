import logging
from contextlib import asynccontextmanager
from pathlib import Path

import firebase_admin
from firebase_admin import credentials
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.core.config import settings

# Routers — imported here; each module is created in its own phase
from src.routers import doi as doi_router
from src.routers import pdf as pdf_router
from src.routers import chat as chat_router
from src.routers import rag as rag_router
from src.routers import storage as storage_router
from src.routers import projects as projects_router
from src.routers import history as history_router

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan handler.
    Firebase Admin SDK is initialised once on startup and cleaned up on shutdown.
    In development mode we still initialise Firebase (needed for Firestore reads).
    If the service-account.json is not yet present we skip silently in dev.
    """
    try:
        options = (
            {"storageBucket": settings.firebase_storage_bucket}
            if settings.firebase_storage_bucket
            else None
        )
        sa_path = Path(settings.firebase_service_account_path)
        if sa_path.exists():
            cred = credentials.Certificate(str(sa_path))
            firebase_admin.initialize_app(cred, options or {})
            logger.info("Firebase Admin SDK initialised via service account file")
        else:
            # Cloud Run path: use Application Default Credentials from workload identity.
            firebase_admin.initialize_app(options=options or {})
            logger.info(
                "Firebase Admin SDK initialised via Application Default Credentials"
            )
    except Exception as exc:
        if settings.is_development:
            logger.warning("Firebase not initialised in development: %s", exc)
        else:
            raise RuntimeError(
                f"Firebase initialisation failed in production: {exc}"
            ) from exc

    yield

    # Cleanup
    if firebase_admin._apps:
        firebase_admin.delete_app(firebase_admin.get_app())
        logger.info("Firebase Admin SDK shut down")


app = FastAPI(
    title="ResearchDoi API",
    description="Backend service for DOI lookup, PDF resolution, RAG, and Gemini chat.",
    version="1.0.0",
    lifespan=lifespan,
)

# ─── CORS ────────────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── Routers ─────────────────────────────────────────────────────────────────
app.include_router(doi_router.router, prefix="/api/doi", tags=["DOI"])
app.include_router(pdf_router.router, prefix="/api/pdf", tags=["PDF"])
app.include_router(chat_router.router, prefix="/api/chat", tags=["Chat"])
app.include_router(rag_router.router, prefix="/api/rag", tags=["RAG"])
app.include_router(storage_router.router, prefix="/api/storage", tags=["Storage"])
app.include_router(projects_router.router, prefix="/api/projects", tags=["Projects"])
app.include_router(history_router.router, prefix="/api/history", tags=["History"])


@app.get("/health", tags=["Health"])
async def health_check():
    return {
        "status": "ok",
        "env": settings.app_env.value,
        "firebase_initialised": bool(firebase_admin._apps),
    }
