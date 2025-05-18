# API Reference

This document describes the main backend endpoints. All endpoints are prefixed
with `/api/v1`.

## Resume Customization

| Method | Path | Description |
| --- | --- | --- |
| `POST` | `/customize/resume` | Start a resume customization job. Returns a `customization_id`. |
| `GET` | `/customize/status/{id}` | Retrieve the current status of a customization job. |
| `WS` | `/ws/customize/{id}?token=...` | Receive progress updates for a running customization. |

### WebSocket Messages

Progress updates are JSON objects of the form:

```json
{
  "stage": "evaluation",
  "percentage": 50,
  "message": "Evaluation complete"
}
```

## Resumes

| Method | Path | Description |
| --- | --- | --- |
| `POST` | `/resumes/` | Create a new resume |
| `GET` | `/resumes/{id}` | Retrieve a resume |
| `POST` | `/resumes/{id}/versions` | Add a new version |

## Job Descriptions

| Method | Path | Description |
| --- | --- | --- |
| `POST` | `/jobs/` | Create a job description |
| `GET` | `/jobs/{id}` | Retrieve a job description |

Additional endpoints are implemented for cover letters, ATS analysis, and file
export. Consult the source code for full details.

