"""Provider and complexity routes shared by the generation APIs.

These endpoints used to be copied on both ``/generate`` and
``/generate-enhanced``. One factory keeps the behavior and the documented
paths, with distinct OpenAPI operation ids for each mount.
"""

from fastapi import APIRouter, HTTPException

from core.config import settings


def build_provider_router(operation_prefix: str) -> APIRouter:
    """Return a new router exposing provider status and complexity controls."""
    router = APIRouter()

    @router.get("/providers", operation_id=f"{operation_prefix}_get_ai_providers")
    async def get_ai_providers():
        """Get information about available AI providers."""
        from services.ai_providers import get_available_providers

        return {
            "current_provider": settings.ai_provider,
            "available_providers": get_available_providers(),
        }

    @router.get(
        "/providers/status",
        operation_id=f"{operation_prefix}_check_provider_status",
    )
    async def check_provider_status():
        """Check the status of the current AI provider."""
        from services.ai_providers import create_ai_provider

        try:
            provider = create_ai_provider()
            is_available = await provider.is_available()
            model_info = provider.get_model_info()
            return {
                "provider": settings.ai_provider,
                "available": is_available,
                "model_info": model_info,
            }
        except Exception as exc:
            return {
                "provider": settings.ai_provider,
                "available": False,
                "error": str(exc),
            }

    @router.get("/complexity", operation_id=f"{operation_prefix}_get_complexity_setting")
    async def get_complexity_setting():
        """Get the current novel complexity setting."""
        return {
            "current_complexity": settings.novel_complexity,
            "available_levels": ["simple", "standard", "complex", "literary"],
            "descriptions": {
                "simple": "Clear, straightforward storytelling with accessible language",
                "standard": "Balanced plot and character development with moderate complexity",
                "complex": "Multi-layered narratives with sophisticated themes and techniques",
                "literary": "Artistic prose with experimental techniques and deep philosophical themes",
            },
        }

    @router.post(
        "/complexity/{level}",
        operation_id=f"{operation_prefix}_set_complexity_level",
    )
    async def set_complexity_level(level: str):
        """Set the novel complexity level for new generations in this process."""
        valid_levels = ["simple", "standard", "complex", "literary"]
        if level not in valid_levels:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid complexity level. Must be one of: {', '.join(valid_levels)}",
            )

        settings.novel_complexity = level
        return {
            "message": f"Complexity level set to '{level}'",
            "new_complexity": level,
            "note": "This setting applies to new generations only",
        }

    return router


def require_story(db, story_id: int):
    """Load a story or raise the API's standard 404."""
    from models.story import Story

    story = db.query(Story).filter(Story.story_id == story_id).first()
    if not story:
        raise HTTPException(status_code=404, detail="Story not found")
    return story
