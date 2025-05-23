import io

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import PlainTextResponse, StreamingResponse
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.resume import Resume, ResumeVersion
from app.services.export_service import (
    convert_markdown_to_docx,
    convert_markdown_to_pdf,
)

router = APIRouter()


@router.get("/resume/{resume_id}/markdown")
def export_resume_as_markdown(
    resume_id: str, version_id: str = None, db: Session = Depends(get_db)
):
    """
    Export a resume as Markdown.

    - **resume_id**: ID of the resume to export
    - **version_id**: Optional ID of a specific version to export (default: latest)
    """
    # Verify the resume exists
    resume = db.query(Resume).filter(Resume.id == resume_id).first()
    if not resume:
        raise HTTPException(status_code=404, detail="Resume not found")

    # Get the specified version or the latest version
    if version_id:
        resume_version = (
            db.query(ResumeVersion)
            .filter(
                ResumeVersion.resume_id == resume_id, ResumeVersion.id == version_id
            )
            .first()
        )
        if not resume_version:
            raise HTTPException(status_code=404, detail="Resume version not found")
    else:
        resume_version = (
            db.query(ResumeVersion)
            .filter(ResumeVersion.resume_id == resume_id)
            .order_by(ResumeVersion.version_number.desc())
            .first()
        )
        if not resume_version:
            raise HTTPException(status_code=404, detail="Resume content not found")

    # Return the markdown content with appropriate headers
    filename = f"{resume.title.replace(' ', '_')}.md"
    return PlainTextResponse(
        content=resume_version.content,
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@router.get("/resume/{resume_id}/pdf")
async def export_resume_as_pdf(
    resume_id: str, version_id: str = None, db: Session = Depends(get_db)
):
    """
    Export a resume as PDF.

    - **resume_id**: ID of the resume to export
    - **version_id**: Optional ID of a specific version to export (default: latest)
    """
    # Verify the resume exists
    resume = db.query(Resume).filter(Resume.id == resume_id).first()
    if not resume:
        raise HTTPException(status_code=404, detail="Resume not found")

    # Get the specified version or the latest version
    if version_id:
        resume_version = (
            db.query(ResumeVersion)
            .filter(
                ResumeVersion.resume_id == resume_id, ResumeVersion.id == version_id
            )
            .first()
        )
        if not resume_version:
            raise HTTPException(status_code=404, detail="Resume version not found")
    else:
        resume_version = (
            db.query(ResumeVersion)
            .filter(ResumeVersion.resume_id == resume_id)
            .order_by(ResumeVersion.version_number.desc())
            .first()
        )
        if not resume_version:
            raise HTTPException(status_code=404, detail="Resume content not found")

    # Convert markdown to PDF
    pdf_bytes = await convert_markdown_to_pdf(resume_version.content)

    # Return the PDF as a streaming response
    filename = f"{resume.title.replace(' ', '_')}.pdf"
    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@router.get("/resume/{resume_id}/docx")
async def export_resume_as_docx(
    resume_id: str, version_id: str = None, db: Session = Depends(get_db)
):
    """
    Export a resume as DOCX.

    - **resume_id**: ID of the resume to export
    - **version_id**: Optional ID of a specific version to export (default: latest)
    """
    # Verify the resume exists
    resume = db.query(Resume).filter(Resume.id == resume_id).first()
    if not resume:
        raise HTTPException(status_code=404, detail="Resume not found")

    # Get the specified version or the latest version
    if version_id:
        resume_version = (
            db.query(ResumeVersion)
            .filter(
                ResumeVersion.resume_id == resume_id, ResumeVersion.id == version_id
            )
            .first()
        )
        if not resume_version:
            raise HTTPException(status_code=404, detail="Resume version not found")
    else:
        resume_version = (
            db.query(ResumeVersion)
            .filter(ResumeVersion.resume_id == resume_id)
            .order_by(ResumeVersion.version_number.desc())
            .first()
        )
        if not resume_version:
            raise HTTPException(status_code=404, detail="Resume content not found")

    # Convert markdown to DOCX
    docx_bytes = await convert_markdown_to_docx(resume_version.content)

    # Return the DOCX as a streaming response
    filename = f"{resume.title.replace(' ', '_')}.docx"
    return StreamingResponse(
        io.BytesIO(docx_bytes),
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )



