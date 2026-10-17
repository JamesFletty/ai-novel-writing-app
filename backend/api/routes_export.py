"""
Export API routes for downloading stories in various formats.
"""
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from db.database import get_db
from services.export_service import export_service
from models.story import Story

router = APIRouter()


@router.get("/stories/{story_id}/export/markdown")
async def export_story_markdown(
    story_id: int,
    db: Session = Depends(get_db)
):
    """
    Export a story as a Markdown file.
    
    Args:
        story_id: ID of the story to export
        db: Database session
        
    Returns:
        FileResponse with the Markdown file
    """
    try:
        # Check if story exists
        story = db.query(Story).filter(Story.story_id == story_id).first()
        if not story:
            raise HTTPException(status_code=404, detail="Story not found")
        
        # Generate export
        filepath = export_service.export_story_markdown(story_id, db)
        
        # Return file
        filename = Path(filepath).name
        return FileResponse(
            path=filepath,
            filename=filename,
            media_type="text/markdown",
        )
        
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Export failed: {str(e)}")


@router.get("/stories/{story_id}/export/text")
async def export_story_text(
    story_id: int,
    db: Session = Depends(get_db)
):
    """
    Export a story as a plain text file.
    
    Args:
        story_id: ID of the story to export
        db: Database session
        
    Returns:
        FileResponse with the text file
    """
    try:
        # Check if story exists
        story = db.query(Story).filter(Story.story_id == story_id).first()
        if not story:
            raise HTTPException(status_code=404, detail="Story not found")
        
        # Generate export
        filepath = export_service.export_story_text(story_id, db)
        
        # Return file
        filename = Path(filepath).name
        return FileResponse(
            path=filepath,
            filename=filename,
            media_type="text/plain",
        )
        
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Export failed: {str(e)}")


@router.get("/stories/{story_id}/export/preview")
async def preview_story_export(
    story_id: int,
    format: str = "markdown",
    db: Session = Depends(get_db)
):
    """
    Preview the export content without downloading.
    
    Args:
        story_id: ID of the story to preview
        format: Export format ("markdown" or "text")
        db: Database session
        
    Returns:
        JSON response with the export content
    """
    try:
        # Check if story exists
        story = db.query(Story).filter(Story.story_id == story_id).first()
        if not story:
            raise HTTPException(status_code=404, detail="Story not found")
        
        if format == "markdown":
            filepath = export_service.export_story_markdown(story_id, db)
            media_type = "text/markdown"
        elif format == "text":
            filepath = export_service.export_story_text(story_id, db)
            media_type = "text/plain"
        else:
            raise HTTPException(status_code=400, detail="Invalid format. Use 'markdown' or 'text'")
        
        # Read the content
        path = Path(filepath)
        content = path.read_text(encoding="utf-8")
        
        # Clean up the temporary file
        path.unlink(missing_ok=True)
        
        return {
            "story_id": story_id,
            "story_title": story.title,
            "format": format,
            "content": content,
            "media_type": media_type
        }
        
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Preview failed: {str(e)}")


@router.get("/stories/{story_id}/export/info")
async def get_export_info(
    story_id: int,
    db: Session = Depends(get_db)
):
    """
    Get information about what would be exported.
    
    Args:
        story_id: ID of the story
        db: Database session
        
    Returns:
        JSON response with export information
    """
    try:
        # Check if story exists
        story = db.query(Story).filter(Story.story_id == story_id).first()
        if not story:
            raise HTTPException(status_code=404, detail="Story not found")
        
        # Get chapter information
        from models.chapter import Chapter
        chapters = db.query(Chapter).filter(
            Chapter.story_id == story_id,
            Chapter.is_generated == True
        ).order_by(Chapter.number).all()
        
        total_words = sum(chapter.word_count or 0 for chapter in chapters)
        
        return {
            "story_id": story_id,
            "story_title": story.title,
            "description": story.description,
            "genre": story.genre,
            "target_chapters": story.target_chapters,
            "target_word_count": story.target_word_count,
            "generated_chapters": len(chapters),
            "current_word_count": total_words,
            "completion_percentage": round((len(chapters) / story.target_chapters) * 100, 1) if story.target_chapters > 0 else 0,
            "chapters": [
                {
                    "number": chapter.number,
                    "title": chapter.title,
                    "word_count": chapter.word_count or 0,
                    "has_content": bool(chapter.content)
                }
                for chapter in chapters
            ],
            "available_formats": ["markdown", "text"],
            "created_at": story.created_at.isoformat(),
            "updated_at": story.updated_at.isoformat() if story.updated_at else None
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get export info: {str(e)}")
