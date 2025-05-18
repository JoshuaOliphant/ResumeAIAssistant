# Developer Guide

This guide explains how to extend the Resume AI Assistant backend. It follows the
best practices in `pydanticai_notes` and the architecture defined in
`spec.md`.

## Architecture Overview

The service uses **PydanticAI** with the evaluator/optimizer pattern. Each stage
of the resume customization process is handled by a dedicated class:

- `ResumeEvaluator`
- `ResumePlanner`
- `ResumeImplementer`
- `ResumeVerifier`

The `ResumeCustomizer` class in `app/services/resume_customizer/executor.py`
coordinates these stages and reports progress via WebSocket.

## Adding New Functionality

1. **Create a Service**
   - Place new business logic under `app/services/`.
   - Write Google‑style docstrings for all public methods.
2. **Expose an Endpoint**
   - Add a new module under `app/api/endpoints/` and include it in
     `app/api/api.py`.
   - Document the endpoint in `API_REFERENCE.md`.
3. **Write Tests**
   - Add unit tests in `tests/unit/`.
   - Run them with `uv run pytest tests/unit` before committing.
4. **Update Documentation**
   - Keep this guide and the API reference up to date.

## Extending PydanticAI

Model configuration is centralized in `app/core/config.py`. When adding new
models or providers, update the configuration helpers and ensure that
environment variables are documented in the README.

## Monitoring and Metrics

Use the utilities in `app/services/metrics.py` and the Logfire integration to
record metrics and traces. Wrap long‑running operations with `track_latency` and
increment counters via `metrics_collector`.

