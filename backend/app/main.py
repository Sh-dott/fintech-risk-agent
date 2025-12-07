"""
Risk Decision Engine REST API

Exposes the decision engine via HTTP endpoints for real-time transaction scoring.
Deploy on cloud platforms (Heroku, AWS, Google Cloud, Azure, etc.)
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pathlib import Path
import uvicorn

# Import route routers
from backend.app.api.routes.health import router as health_router
from backend.app.api.routes.scoring import router as scoring_router
from backend.app.api.routes.analytics import router as analytics_router
from backend.app.api.routes.dashboard import router as dashboard_router
from backend.app.api.routes.advanced_analytics_routes import router as advanced_analytics_router

# ============================================================================
# FastAPI Application Setup
# ============================================================================

app = FastAPI(
    title="Risk Decision Engine API",
    description="Real-time transaction scoring & fraud detection for fintech payments",
    version="1.0.0",
    docs_url="/api-docs",  # Swagger UI (custom path)
    redoc_url="/api-redoc"  # ReDoc UI (custom path)
)

# Add CORS for web access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================================================================
# Register Route Routers
# ============================================================================

app.include_router(health_router)
app.include_router(scoring_router)
app.include_router(analytics_router)
app.include_router(dashboard_router)
app.include_router(advanced_analytics_router)

# ============================================================================
# Mount static files (frontend dist)
# ============================================================================

# After Vite builds the frontend, serve static assets
frontend_dist = Path(__file__).parent.parent.parent / "frontend" / "dist"
if frontend_dist.exists():
    app.mount("/assets", StaticFiles(directory=frontend_dist / "assets"), name="assets")

# ============================================================================
# Startup & Shutdown Events
# ============================================================================

@app.on_event("startup")
async def startup_event():
    """Initialize on startup."""
    print("[OK] Risk Decision Engine API started")
    print("[INFO] API Documentation: http://localhost:8000/api-docs")
    print("[INFO] Dashboard: http://localhost:8000/")


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown."""
    print("[STOP] Risk Decision Engine API stopped")


# ============================================================================
# Main Entry Point
# ============================================================================

if __name__ == "__main__":
    uvicorn.run(
        "backend.app.main:app",
        host="0.0.0.0",  # Listen on all interfaces
        port=8000,
        reload=True  # Auto-reload on file changes (development only)
    )
