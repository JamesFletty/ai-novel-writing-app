"""
Enhanced API routes for AI generation functionality.

Updated to use the enhanced generation service for better quality output.
Provider, complexity, and outline routes live with the standard generation
API (or the shared provider router) so they are not duplicated here.
"""
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
import json

from api.generation_meta import require_story
from db.database import get_db
from models.chapter import Chapter
from schemas.generation import (
    EnhancedChapterGenerateRequest,
    MultiPassGenerateRequest,
    RegenerateChapterRequest,
)
from services.enhanced_generation_service import EnhancedGenerationService

router = APIRouter()


@router.post("/stories/{story_id}/chapters/{chapter_number}")
async def generate_chapter_enhanced(
    story_id: int,
    chapter_number: int,
    request: EnhancedChapterGenerateRequest,
    stream: bool = False,
    db: Session = Depends(get_db)
):
    """
    Generate chapter content using enhanced prompting and quality controls.

    Args:
        story_id: ID of the story
        chapter_number: Chapter number to generate
        custom_prompt: Optional custom prompt override
        target_word_count: Target word count (1500-5000)
        quality_check: Whether to perform quality assessment
        stream: Whether to stream the response
        db: Database session

    Returns:
        Generated chapter content with metadata
    """
    require_story(db, story_id)

    enhanced_service = EnhancedGenerationService(db)

    if stream:
        # Return streaming response
        async def generate_stream():
            try:
                result_generator = await enhanced_service.generate_chapter_enhanced(
                    story_id=story_id,
                    chapter_number=chapter_number,
                    custom_prompt=request.custom_prompt,
                    target_word_count=request.target_word_count,
                    stream=True,
                    quality_check=request.quality_check
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

    result = await enhanced_service.generate_chapter_enhanced(
        story_id=story_id,
        chapter_number=chapter_number,
        custom_prompt=request.custom_prompt,
        target_word_count=request.target_word_count,
        stream=False,
        quality_check=request.quality_check
    )
    return result


@router.post("/stories/{story_id}/chapters/{chapter_number}/multi-pass")
async def generate_chapter_multi_pass(
    story_id: int,
    chapter_number: int,
    request: MultiPassGenerateRequest,
    db: Session = Depends(get_db)
):
    """
    Generate chapter using multi-pass approach for highest quality.

    This method uses three passes:
    1. Structure and plot beats
    2. Character development and dialogue
    3. Prose refinement and expansion

    Takes longer but produces higher quality results.
    """
    require_story(db, story_id)

    enhanced_service = EnhancedGenerationService(db)

    result = await enhanced_service.generate_chapter_multi_pass(
        story_id=story_id,
        chapter_number=chapter_number,
        target_word_count=request.target_word_count
    )

    return result


@router.post("/stories/{story_id}/chapters/{chapter_number}/analyze-quality")
async def analyze_chapter_quality(
    story_id: int,
    chapter_number: int,
    db: Session = Depends(get_db)
):
    """
    Analyze the quality of an existing chapter.

    Returns quality metrics and improvement suggestions.
    """
    story = require_story(db, story_id)

    chapter = db.query(Chapter).filter(
        Chapter.story_id == story_id,
        Chapter.number == chapter_number
    ).first()

    if not chapter or not chapter.content:
        raise HTTPException(status_code=404, detail="Chapter not found or has no content")

    enhanced_service = EnhancedGenerationService(db)
    previous_chapters = enhanced_service._get_previous_chapters(story_id, chapter_number)

    target_word_count = max(
        1500,
        min(5000, round((story.target_word_count or 50000) / max(story.target_chapters or 20, 1))),
    )
    quality_score = enhanced_service._assess_content_quality(
        chapter.content,
        target_word_count,
        previous_chapters
    )

    # Analyze specific issues
    analysis = {
        "quality_score": quality_score,
        "word_count": len(chapter.content.split()),
        "paragraph_count": len([p for p in chapter.content.split('\n\n') if p.strip()]),
        "dialogue_count": chapter.content.count('"'),
        "issues": [],
        "suggestions": []
    }

    # Check for specific issues
    content_lower = chapter.content.lower()
    banned_phrases = [
        "little did", "unbeknownst", "time seemed to slow", "heart pounded",
        "blood ran cold", "breath caught", "world spun"
    ]

    for phrase in banned_phrases:
        if phrase in content_lower:
            analysis["issues"].append(f"Contains clichéd phrase: '{phrase}'")
            analysis["suggestions"].append(f"Remove or rephrase instances of '{phrase}'")

    if analysis["word_count"] < 1500:
        analysis["issues"].append("Chapter is too short")
        analysis["suggestions"].append("Expand with more detailed scenes, dialogue, and description")

    if analysis["dialogue_count"] < 4:
        analysis["issues"].append("Insufficient dialogue")
        analysis["suggestions"].append("Add more character conversations and interactions")

    if analysis["paragraph_count"] < 6:
        analysis["issues"].append("Too few paragraphs - may lack structure")
        analysis["suggestions"].append("Break content into more distinct scenes and moments")

    return analysis


@router.post("/stories/{story_id}/chapters/{chapter_number}/regenerate")
async def regenerate_chapter_with_feedback(
    story_id: int,
    chapter_number: int,
    request: RegenerateChapterRequest,
    db: Session = Depends(get_db)
):
    """
    Regenerate a chapter with specific feedback incorporated.

    Args:
        story_id: ID of the story
        chapter_number: Chapter number to regenerate
        feedback: Specific feedback on what to improve
        target_word_count: Target word count for regeneration
    """
    require_story(db, story_id)

    enhanced_service = EnhancedGenerationService(db)

    result = await enhanced_service.generate_chapter_enhanced(
        story_id=story_id,
        chapter_number=chapter_number,
        custom_prompt=f"Specific revision feedback: {request.feedback}",
        target_word_count=request.target_word_count,
        quality_check=True
    )

    return result
