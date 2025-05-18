"""Endpoints for Claude Code resume customization workflow."""

from __future__ import annotations

import asyncio
import json
import uuid
from datetime import datetime
from typing import Dict

import logfire
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, WebSocket, WebSocketDisconnect

from app.services.websocket_manager import WebSocketManager
from app.services.claude_code.executor import ResumeCustomizer

router = APIRouter()

# Simple in-memory storage for demo purposes
CUSTOMIZATION_RESULTS: Dict[str, dict] = {}
CUSTOMIZATION_STATUS: Dict[str, dict] = {}
WEBSOCKETS = WebSocketManager()


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
        CUSTOMIZATION_RESULTS[customization_id] = result
        CUSTOMIZATION_STATUS[customization_id] = {
            "status": "completed" if result.get("success") else "failed",
            "completed_at": datetime.utcnow().isoformat(),
            "result": result,
        }
    except Exception as exc:  # pragma: no cover - unexpected
        logfire.error("Customization task failed", error=str(exc), exc_info=True)
        CUSTOMIZATION_STATUS[customization_id] = {
            "status": "failed",
            "error": str(exc),
            "completed_at": datetime.utcnow().isoformat(),
        }


def calculate_overall_progress(stage: str, percentage: int) -> int:
    weights = {
        "evaluation": 0.25,
        "planning": 0.25,
        "implementation": 0.35,
        "verification": 0.15,
    }
    order = ["evaluation", "planning", "implementation", "verification"]
    index = order.index(stage) if stage in order else 0
    completed = sum(weights[order[i]] for i in range(index)) * 100
    current = weights.get(stage, 0) * percentage
    return round(completed + current)


@router.websocket("/ws/customize/{customization_id}")
async def websocket_progress(
    websocket: WebSocket,
    customization_id: str,
    token: str | None = Query(None),
):
    """WebSocket endpoint for progress updates."""
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

