"""Streaming helper for token-by-token updates.

This utility is inspired by the streaming implementation notes
in ``pydanticai_notes/12_streaming_implementation.md``. It allows
streaming model output token by token while tracking usage and
forwarding updates via a WebSocket progress callback.
"""

from typing import Any, AsyncGenerator, Awaitable, Callable

import logfire
from pydantic_ai import Agent


class LogStreamer:
    """Stream model responses token by token."""

    def __init__(
        self,
        agent: Agent,
        progress_callback: Callable[[str], Awaitable[None]] | None = None,
    ) -> None:
        self.agent = agent
        self.progress_callback = progress_callback
        self.input_tokens = 0
        self.output_tokens = 0

    async def run(self, prompt: str) -> Any:
        """Run the agent and stream tokens as they are produced."""
        async with self.agent.run_stream(prompt) as result:
            async for token in result.token_stream():
                self.output_tokens += 1
                if self.progress_callback:
                    try:
                        await self.progress_callback(token)
                    except Exception as exc:  # pragma: no cover - log but continue
                        logfire.warning(
                            "Progress callback failed", error=str(exc)
                        )
            final = await result.final()
            self.input_tokens = result.metrics.input_tokens
            self.output_tokens = result.metrics.output_tokens
        return final

    async def token_stream(self, prompt: str) -> AsyncGenerator[str, None]:
        """Yield tokens for a prompt one by one."""
        async with self.agent.run_stream(prompt) as result:
            async for token in result.token_stream():
                self.output_tokens += 1
                yield token
            self.input_tokens = result.metrics.input_tokens
            self.output_tokens = result.metrics.output_tokens
            yield await result.final()
