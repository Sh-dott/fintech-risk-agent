"""
Dashboard serving endpoints for Risk Decision Engine API
"""

from fastapi import APIRouter
from fastapi.responses import FileResponse
from pathlib import Path

router = APIRouter(tags=["Dashboard"])

# Path to frontend files (serving directly, not from dist)
FRONTEND_DIR = Path(__file__).parent.parent.parent.parent.parent / "frontend"


@router.get("/", include_in_schema=False)
async def root():
    """Serve the modern fraud detection dashboard."""
    return FileResponse(
        FRONTEND_DIR / "index.html",
        media_type="text/html"
    )


@router.get("/dashboard", include_in_schema=False)
async def get_dashboard():
    """Get the modern interactive web dashboard."""
    return FileResponse(
        FRONTEND_DIR / "index.html",
        media_type="text/html"
    )


@router.get("/classic", include_in_schema=False)
async def get_classic_dashboard():
    """Get the classic dashboard."""
    return FileResponse(
        FRONTEND_DIST / "classic.html",
        media_type="text/html"
    )


@router.get("/enhanced", include_in_schema=False)
async def get_enhanced_dashboard():
    """Get the ultra-modern enhanced analytics dashboard."""
    return FileResponse(
        FRONTEND_DIST / "enhanced.html",
        media_type="text/html"
    )


@router.get("/docs", include_in_schema=False)
async def get_docs():
    """Interactive API documentation (Swagger UI)."""
    return FileResponse(
        FRONTEND_DIST / "index.html",
        media_type="text/html"
    )
