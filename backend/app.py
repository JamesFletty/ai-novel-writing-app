"""
Main FastAPI application entry point.

This creates the FastAPI app instance and includes all the routers.
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from core.config import settings
from db.database import create_tables
from api.generation_meta import build_provider_router
from api.routes_story import router as story_router
from api.routes_character import router as character_router
from api.routes_world import router as world_router
from api.routes_generate import router as generate_router
from api.routes_generate_enhanced import router as enhanced_generate_router
from api.routes_export import router as export_router
from services.ai_providers import close_ai_providers


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager.
    
    Handles startup and shutdown events.
    """
    # Startup
    print("Starting AI Novel App backend...")
    
    # Create database tables
    create_tables()
    print("Database tables created/verified")
    
    yield

    # Shutdown
    await close_ai_providers()
    print("Shutting down AI Novel App backend...")


# Create FastAPI application
app = FastAPI(
    title=settings.project_name,
    version=settings.version,
    description="AI-powered novel writing application backend with enhanced generation",
    lifespan=lifespan
)

# Add CORS middleware
# Include API routers
app.include_router(story_router, prefix=f"{settings.api_v1_prefix}/stories", tags=["stories"])
app.include_router(character_router, prefix=f"{settings.api_v1_prefix}/characters", tags=["characters"])
app.include_router(world_router, prefix=f"{settings.api_v1_prefix}/world", tags=["world"])
app.include_router(generate_router, prefix=f"{settings.api_v1_prefix}/generate", tags=["generation"])
app.include_router(
    build_provider_router("generate"),
    prefix=f"{settings.api_v1_prefix}/generate",
    tags=["generation"],
)
app.include_router(
    enhanced_generate_router,
    prefix=f"{settings.api_v1_prefix}/generate-enhanced",
    tags=["enhanced-generation"],
)
app.include_router(
    build_provider_router("generate_enhanced"),
    prefix=f"{settings.api_v1_prefix}/generate-enhanced",
    tags=["enhanced-generation"],
)
app.include_router(export_router, prefix=f"{settings.api_v1_prefix}/export", tags=["export"])

# Add CORS middleware after routes
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    # Starlette does not allow credentialed wildcard CORS responses.  Keep
    # credentials enabled for explicit origins and fail safe for legacy "*" envs.
    allow_credentials="*" not in settings.cors_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    """Root endpoint with basic API information."""
    return {
        "message": "AI Novel Writing App API",
        "version": settings.version,
        "docs_url": "/docs",
        "status": "running",
        "ai_provider": settings.ai_provider,
    }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}


@app.get(f"{settings.api_v1_prefix}/features")
async def get_frontend_features():
    """Feature flags consumed by the React chapter editor."""
    return {
        "enhanced_generation": True,
        "multi_pass_generation": True,
        "quality_analysis": True,
        "custom_prompting": True,
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.debug
    )
