"""
API routes for AI generation functionality.
"""
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session, sessionmaker
import json

from api.generation_meta import require_story
from db.database import get_db
from schemas.story import OutlineGenerateRequest, OutlineResponse
from schemas.character import CharacterGenerateRequest, CharacterGenerateResponse
from schemas.generation import ChapterExpandRequest, ChapterGenerateRequest
from services.generation_service import GenerationService

router = APIRouter()


@router.post("/stories/{story_id}/outline", response_model=OutlineResponse)
async def generate_outline(
    story_id: int,
    request: OutlineGenerateRequest,
    db: Session = Depends(get_db)
):
    """
    Generate an outline for a story.
    
    Args:
        story_id: ID of the story
        request: Outline generation parameters
        db: Database session
        
    Returns:
        Generated outline
    """
    require_story(db, story_id)
    
    # Generate outline
    generation_service = GenerationService(db)
    try:
        result = await generation_service.generate_outline(
            story_id=story_id,
            target_chapters=request.target_chapters,
            custom_prompt=request.custom_prompt
        )
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    
    return result


@router.post("/stories/{story_id}/chapters/{chapter_number}")
async def generate_chapter(
    story_id: int,
    chapter_number: int,
    request: ChapterGenerateRequest,
    stream: bool = False,
    db: Session = Depends(get_db)
):
    """
    Generate content for a specific chapter.
    
    Args:
        story_id: ID of the story
        chapter_number: Chapter number to generate
        custom_prompt: Optional custom prompt
        stream: Whether to stream the response
        db: Database session
        
    Returns:
        Generated chapter content (streaming or complete)
    """
    require_story(db, story_id)
    
    generation_service = GenerationService(db)
    
    if stream:
        # Return streaming response
        async def generate_stream():
            try:
                result_generator = generation_service.generate_chapter_stream(
                    story_id=story_id,
                    chapter_number=chapter_number,
                    custom_prompt=request.custom_prompt
                )
                async for chunk in result_generator:
                    yield f"data: {json.dumps(chunk)}\n\n"
            except Exception as e:
                error_chunk = {
                    "type": "error",
                    "success": False,
                    "error": str(e),
                    "error_type": type(e).__name__
                }
                yield f"data: {json.dumps(error_chunk)}\n\n"
        
        return StreamingResponse(
            generate_stream(),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "Connection": "keep-alive"}
        )
    else:
        # Return complete response
        result = await generation_service.generate_chapter(
            story_id=story_id,
            chapter_number=chapter_number,
            custom_prompt=request.custom_prompt,
            stream=False
        )
        return result


@router.post("/stories/{story_id}/chapters/{chapter_number}/expand")
async def expand_chapter(
    story_id: int,
    chapter_number: int,
    request: ChapterExpandRequest,
    db: Session = Depends(get_db),
):
    """Expand or refine an existing chapter and preserve its previous revision."""
    require_story(db, story_id)

    service = GenerationService(db)
    try:
        return await service.expand_chapter(
            story_id=story_id,
            chapter_number=chapter_number,
            expansion_type=request.expansion_type,
            custom_prompt=request.custom_prompt,
            target_length=request.target_length,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/stories/{story_id}/characters", response_model=CharacterGenerateResponse)
async def generate_characters(
    story_id: int,
    request: CharacterGenerateRequest,
    db: Session = Depends(get_db)
):
    """
    Generate characters for a story.

    Args:
        story_id: ID of the story
        request: Character generation parameters
        db: Database session

    Returns:
        Generated characters
    """
    require_story(db, story_id)

    # Generate characters
    generation_service = GenerationService(db)
    result = await generation_service.generate_characters(
        story_id=story_id,
        character_count=request.character_count,
        custom_prompt=request.custom_prompt,
    )

    return result


@router.post("/stories/{story_id}/world")
async def generate_world_elements(
    story_id: int,
    element_count: int = 8,
    db: Session = Depends(get_db)
):
    """
    Generate world building elements for a story.

    Args:
        story_id: ID of the story
        element_count: Number of world elements to generate
        db: Database session

    Returns:
        Generated world elements
    """
    require_story(db, story_id)

    # Generate world elements
    generation_service = GenerationService(db)
    result = await generation_service.generate_world_elements(
        story_id=story_id,
        element_count=element_count
    )

    return result


@router.post("/stories/{story_id}/chapters/{chapter_number}/edit")
async def edit_chapter_content(
    story_id: int,
    chapter_number: int,
    instruction: str,
    paragraph: str,
    db: Session = Depends(get_db)
):
    """
    AI-assisted editing of chapter content.

    Args:
        story_id: ID of the story
        chapter_number: Chapter number
        instruction: Editing instruction (e.g., "make more suspenseful")
        paragraph: Text to edit
        db: Database session

    Returns:
        Edited text
    """
    story = require_story(db, story_id)

    generation_service = GenerationService(db)

    try:
        # Use the editing prompt template
        from utils.prompt_templates import PromptTemplates
        prompt_templates = PromptTemplates()

        prompt = prompt_templates.get_editing_prompt(
            original_text=paragraph,
            instruction=instruction,
            context=f"Chapter {chapter_number} of '{story.title}'"
        )

        # Use creative writing parameters for editing
        from services.ai_providers.base import GenerationParams
        params = GenerationParams.for_creative_writing()
        params.max_tokens = 2000

        result = await generation_service.ai_provider.generate_text(prompt, params)

        return {
            "success": True,
            "original_text": paragraph,
            "edited_text": result.text,
            "instruction": instruction,
            "tokens_used": result.tokens_used
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "original_text": paragraph,
            "edited_text": paragraph,
            "instruction": instruction
        }


@router.post("/enhance-sophistication")
async def enhance_text_sophistication(
    text: str,
    focus_area: str = "general",
    db: Session = Depends(get_db)
):
    """
    Enhance text sophistication and originality.

    Args:
        text: Text to enhance
        focus_area: Area to focus on (dialogue, description, pacing, character, general)
        db: Database session

    Returns:
        Enhanced text with improved sophistication
    """
    generation_service = GenerationService(db)

    try:
        from utils.prompt_templates import PromptTemplates
        prompt_templates = PromptTemplates()

        prompt = prompt_templates.get_sophistication_prompt(
            original_text=text,
            focus_area=focus_area
        )

        # Use creative writing parameters for sophistication enhancement
        from services.ai_providers.base import GenerationParams
        params = GenerationParams.for_creative_writing()
        params.max_tokens = len(text.split()) * 2  # Allow for expansion

        result = await generation_service.ai_provider.generate_text(prompt, params)

        return {
            "success": True,
            "original_text": text,
            "enhanced_text": result.text,
            "focus_area": focus_area,
            "tokens_used": result.tokens_used,
            "improvement_notes": f"Enhanced for {focus_area} sophistication"
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "original_text": text,
            "enhanced_text": text,
            "focus_area": focus_area
        }


@router.post("/stories/{story_id}/full-draft")
async def generate_full_draft(
    story_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    Generate a complete novel draft (outline + all chapters).
    
    This is a long-running operation that runs in the background.
    
    Args:
        story_id: ID of the story
        background_tasks: FastAPI background tasks
        db: Database session
        
    Returns:
        Task started confirmation
    """
    require_story(db, story_id)

    # The request-scoped session is closed after the response. Build a fresh
    # session factory against the same engine for the background task.
    task_session_factory = sessionmaker(
        autocommit=False,
        autoflush=False,
        bind=db.get_bind(),
    )

    async def generate_full_novel():
        """Background task to generate complete novel."""
        task_db = task_session_factory()
        try:
            generation_service = GenerationService(task_db)

            # First generate outline
            outline_result = await generation_service.generate_outline(story_id)
            if not outline_result.get("success"):
                return

            # Then generate all chapters
            chapters = outline_result.get("outline", {}).get("chapters", [])
            for chapter_data in chapters:
                chapter_number = chapter_data["number"]
                chapter_result = await generation_service.generate_chapter(
                    story_id=story_id,
                    chapter_number=chapter_number
                )
                if not chapter_result.get("success"):
                    return
        finally:
            task_db.close()
    
    # Add to background tasks
    background_tasks.add_task(generate_full_novel)
    
    return {
        "message": "Full draft generation started",
        "story_id": story_id,
        "status": "in_progress"
    }
