"""
main.py — FastAPI Application Factory
--------------------------------------
This is the entry point of your entire backend.

KEY CONCEPTS IN THIS FILE:
  1. FastAPI() — creates your app instance (like express() in Node)
  2. @app.get("/") — a "decorator" that registers a URL route
  3. lifespan — startup/shutdown logic (connect DB, load models)
  4. CORS — allows your Next.js frontend (different port) to call this API

WHAT IS A ROUTE?
  When a browser/app calls GET http://localhost:8000/health,
  FastAPI matches that to the function decorated with @app.get("/health")
  and runs it. That's all a web framework does — match URLs to functions.
"""

from contextlib import asynccontextmanager
import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.db.init_db import init_mongodb
from app.services.redis_cache import redis_service
from fastapi_limiter import FastAPILimiter

# Configure logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ── Lifespan: runs code at startup and shutdown ───────────────────────────────
# This is where we connect MongoDB, load spaCy model, init ChromaDB
@asynccontextmanager
async def lifespan(app: FastAPI):
    # ── STARTUP ──────────────────────────────────────────────────
    logger.info(f"Starting up {settings.APP_NAME}...")
    print(f"\n[STARTUP] {settings.APP_NAME} is starting up...")
    print(f"   Environment : {settings.APP_ENV}")
    print(f"   Debug Mode  : {settings.DEBUG}")
    print(f"   Docs URL    : http://localhost:8000/docs\n")
    
    # Initialize Database (MongoDB + Beanie)
    try:
        await init_mongodb()
    except Exception as e:
        print(f"[ERROR] Failed to connect to MongoDB: {e}")
        print("[WARNING] The app is running, but database operations will fail until MongoDB is running.")

    # Initialize Redis
    await redis_service.connect()
    
    # Initialize FastAPILimiter
    if redis_service.redis_client:
        await FastAPILimiter.init(redis_service.redis_client)

    yield  # ← App runs while waiting here

    # ── SHUTDOWN ─────────────────────────────────────────────────
    print("\n[SHUTDOWN] Shutting down Smart Document Hub...")
    await redis_service.disconnect()


# ── Create FastAPI App ────────────────────────────────────────────────────────
app = FastAPI(
    title=settings.APP_NAME,
    description="A production-grade multilingual document intelligence platform.",
    version="1.0.0",
    docs_url="/docs",       # Swagger UI  → http://localhost:8000/docs
    redoc_url="/redoc",     # ReDoc UI    → http://localhost:8000/redoc
    lifespan=lifespan,
)


# ── CORS Middleware ───────────────────────────────────────────────────────────
# CORS = Cross-Origin Resource Sharing
# Without this, your Next.js app on port 3000 can't call this API on port 8000
# Browsers block cross-origin requests by default (security feature).
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",   # Next.js dev server
        "http://localhost:80",     # Nginx in production
    ],
    allow_credentials=True,       # Allow cookies (needed for JWT in cookies)
    allow_methods=["*"],          # GET, POST, PUT, DELETE, etc.
    allow_headers=["*"],          # Authorization, Content-Type, etc.
)


# ── Routes ───────────────────────────────────────────────────────────────────

@app.get("/", tags=["Root"])
async def root():
    """
    Root endpoint. Returns basic app info.
    The 'async' keyword means FastAPI can handle other requests
    while waiting for this one — important for I/O heavy apps like ours.
    """
    return {
        "app": settings.APP_NAME,
        "version": "1.0.0",
        "status": "running",
        "docs": "/docs",
    }


@app.get("/health", tags=["Health"])
async def health_check():
    """
    Health check endpoint.
    Used by Docker, Kubernetes, and load balancers to know if the app is alive.
    Convention: return 200 OK when healthy.
    """
    return {
        "status": "ok",
        "environment": settings.APP_ENV,
        "debug": settings.DEBUG,
    }


# ── Include Versioned API Router ──────────────────────────────────────────────
from app.api.v1 import router as api_v1_router

app.include_router(api_v1_router, prefix="/api/v1")

