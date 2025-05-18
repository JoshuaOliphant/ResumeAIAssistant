"""Endpoints for resume customization workflow."""

from __future__ import annotations

import asyncio
import json
import uuid
from datetime import datetime
from typing import Dict

import logfire
from fastapi import (
    APIRouter,
    BackgroundTasks,
    HTTPException,
    Query,
    WebSocket,
    WebSocketDisconnect,
)

from app.services.sanitization import sanitize_text
from app.services.token_validation import validate_token

from app.services.websocket_manager import WebSocketManager
from app.services.resume_customizer.executor import ResumeCustomizer

router = APIRouter()

from collections import OrderedDict
from datetime import datetime, timedelta

# Size-limited in-memory storage with automatic cleanup
MAX_STORED_RESULTS = 1000
RESULT_EXPIRY_HOURS = 24
CUSTOMIZATION_RESULTS: OrderedDict[str, dict] = OrderedDict()
CUSTOMIZATION_STATUS: OrderedDict[str, dict] = OrderedDict()
WEBSOCKETS = WebSocketManager()

def cleanup_old_results():
    """Remove expired results and limit total stored items."""
    expiry_time = datetime.utcnow() - timedelta(hours=RESULT_EXPIRY_HOURS)
    # Remove expired items
    for storage in [CUSTOMIZATION_RESULTS, CUSTOMIZATION_STATUS]:
        expired_keys = [
            k for k, v in list(storage.items())
            if "created_at" in v and datetime.fromisoformat(v["created_at"]) < expiry_time
        ]
        for k in expired_keys:
            storage.pop(k, None)
        
        # Enforce size limit
        while len(storage) > MAX_STORED_RESULTS:
            storage.popitem(last=False)  # Remove oldest item


@router.post("/customize/resume")
async def customize_resume(
    resume_content: str,
    job_description: str,
    template_id: str,
    background_tasks: BackgroundTasks,
) -> dict:
    """Initiate resume customization process."""
    customization_id = uuid.uuid4().hex
    CUSTOMIZATION_STATUS[customization_id] = {
        "status": "pending",
        "created_at": datetime.utcnow().isoformat(),
    }

    customizer = ResumeCustomizer()

    async def progress(stage: str, percentage: int, message: str) -> None:
        data = {
            "stage": stage,
            "percentage": percentage,
            "message": message,
        }
        await WEBSOCKETS.send_json(customization_id, data)
        CUSTOMIZATION_STATUS[customization_id] = {
            "status": stage,
            "percentage": percentage,
            "message": message,
        }

    customizer.set_progress_callback(progress)

    background_tasks.add_task(
        run_customization_process,
        customizer,
        resume_content,
        job_description,
        template_id,
        customization_id,
    )

    return {"customization_id": customization_id, "status": "pending"}


async def run_customization_process(
    resume_customizer: ResumeCustomizer,
    resume_content: str,
    job_description: str,
    template_id: str,
    customization_id: str,
) -> None:
    """Run customization workflow and store result."""
    try:
        result = await resume_customizer.customize_resume(
            resume_content=resume_content,
            job_description=job_description,
            template_id=template_id,
            customization_id=customization_id,
        )
        CUSTOMIZATION_RESULTS[customization_id] = {
            **result,
            "original_resume": sanitize_text(result.get("original_resume", "")),
            "customized_resume": sanitize_text(result.get("customized_resume", "")),
        }
        CUSTOMIZATION_STATUS[customization_id] = {
            "status": "completed" if result.get("success") else "failed",
            "completed_at": datetime.utcnow().isoformat(),
            "result": CUSTOMIZATION_RESULTS[customization_id],
        }
    except Exception as exc:  # pragma: no cover - unexpected
        logfire.error("Customization task failed", error=str(exc), exc_info=True)
        CUSTOMIZATION_STATUS[customization_id] = {
            "status": "failed",
            "error": str(exc),
            "completed_at": datetime.utcnow().isoformat(),
        }



@router.websocket("/ws/customize/{customization_id}")
async def websocket_progress(
    websocket: WebSocket,
    customization_id: str,
    token: str | None = Query(None),
):
    """WebSocket endpoint for progress updates."""
    if token is None or not validate_token(token, customization_id):
        await websocket.close(code=1008)
        return
    await websocket.accept()
    WEBSOCKETS.register(customization_id, websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        WEBSOCKETS.remove(customization_id, websocket)


@router.get("/customize/status/{customization_id}")
async def get_status(customization_id: str) -> dict:
    """Retrieve status of a customization job."""
    if customization_id not in CUSTOMIZATION_STATUS:
        raise HTTPException(status_code=404, detail="Not found")
    return CUSTOMIZATION_STATUS[customization_id]

