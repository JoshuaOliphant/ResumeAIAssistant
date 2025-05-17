from __future__ import annotations

import logging
import time
from typing import Dict, Optional

from .websocket_manager import WebSocketManager

logger = logging.getLogger(__name__)


class ProgressTracker:
    """Track and broadcast progress for a resume customization."""

    STAGES = ["evaluation", "planning", "implementation", "verification"]
    STAGE_WEIGHTS = {
        "evaluation": 0.2,
        "planning": 0.3,
        "implementation": 0.4,
        "verification": 0.1,
    }

    def __init__(self, customization_id: str, websocket_manager: WebSocketManager) -> None:
        """Initialize the tracker with the target customization ID."""
        self.customization_id = customization_id
        self.websocket_manager = websocket_manager
        self.stage_statuses: Dict[str, Dict[str, Optional[float | str]]] = {
            stage: {"status": "pending", "progress": 0, "details": None} for stage in self.STAGES
        }
        self.overall_progress = 0
        self.status = "not_started"
        self.start_time: Optional[float] = None
        self.end_time: Optional[float] = None

    async def start(self) -> None:
        """Mark tracking as started and send the initial update."""
        self.start_time = time.time()
        self.status = "in_progress"
        await self._send_update()

    async def update_stage(
        self,
        stage: str,
        status: str,
        progress: Optional[int] = None,
        details: Optional[str] = None,
    ) -> None:
        """Update a stage and broadcast the change."""
        if stage not in self.stage_statuses:
            logger.warning("Unknown stage %s", stage)
            return

        self.stage_statuses[stage]["status"] = status
        if progress is not None:
            self.stage_statuses[stage]["progress"] = max(0, min(100, progress))
        if details:
            self.stage_statuses[stage]["details"] = details

        self._recalculate_overall_progress()
        await self._send_update()

    async def complete(self, success: bool = True) -> None:
        """Finalize tracking with a success or failure state."""
        self.status = "completed" if success else "failed"
        self.end_time = time.time()
        self.overall_progress = 100 if success else self.overall_progress
        await self._send_update()

    def _recalculate_overall_progress(self) -> None:
        """Recalculate the weighted overall progress percentage."""
        total_weight = 0
        weighted_progress = 0
        for stage, info in self.stage_statuses.items():
            weight = self.STAGE_WEIGHTS.get(stage, 0)
            total_weight += weight
            stage_progress = info.get("progress", 0)
            weighted_progress += stage_progress * weight

        if total_weight > 0:
            self.overall_progress = int(weighted_progress / total_weight)
        else:
            self.overall_progress = 0

    async def _send_update(self) -> None:
        """Serialize the current state and send it via WebSocket."""
        update = {
            "overall_progress": self.overall_progress,
            "status": self.status,
            "task_statuses": self.stage_statuses,
            "elapsed_seconds": int(time.time() - self.start_time) if self.start_time else 0,
            "estimated_remaining_seconds": self._estimate_remaining_time(),
        }
        await self.websocket_manager.send_json(
            self.customization_id,
            {"type": "progress_update", "payload": update},
        )

    def _estimate_remaining_time(self) -> Optional[int]:
        """Estimate the remaining time based on progress so far."""
        if self.overall_progress <= 0 or not self.start_time:
            return None
        elapsed = time.time() - self.start_time
        if self.overall_progress > 0:  # Ensure non-zero denominator
            estimated_total = elapsed / (self.overall_progress / 100)
            remaining = estimated_total - elapsed
            return min(int(remaining), 300)
        return None
