# 06 — API Specification

## Purpose

Define the FastAPI REST and SSE endpoints for VisionOps.

## Base URL

```
http://localhost:8001/api
```

## Endpoints

### Health Check

```
GET /api/health
```

Response:
```json
{
  "status": "healthy",
  "version": "0.1.0"
}
```

### Upload Document

```
POST /api/documents
Content-Type: multipart/form-data
```

Request: Form field `file` containing PDF

Response (201):
```json
{
  "document_id": "uuid",
  "filename": "paper.pdf",
  "page_count": 5,
  "status": "uploaded"
}
```

Errors:
- 400: Invalid file type / too large
- 422: Validation error

### Start Analysis Run

```
POST /api/runs
Content-Type: application/json
```

Request:
```json
{
  "document_id": "uuid",
  "skill": "technical_document_to_diagram"
}
```

Response (202):
```json
{
  "run_id": "uuid",
  "status": "started"
}
```

Errors:
- 404: Document not found
- 400: Invalid skill name

### Get Run Status

```
GET /api/runs/{run_id}
```

Response:
```json
{
  "run_id": "uuid",
  "status": "running|completed|failed",
  "skill": "technical_document_to_diagram",
  "iteration": 1,
  "created_at": "ISO8601",
  "updated_at": "ISO8601"
}
```

### Stream Run Events (SSE)

```
GET /api/runs/{run_id}/events
Accept: text/event-stream
```

Event format:
```
event: concepts_extracted
data: {"event": "concepts_extracted", "timestamp": "ISO8601", "data": {"count": 12}}
```

### Get Run Result

```
GET /api/runs/{run_id}/result
```

Response:
```json
{
  "run_id": "uuid",
  "status": "completed",
  "concepts": [...],
  "relationships": [...],
  "equations": [...],
  "diagram_spec": {...},
  "diagram_svg": "...",
  "critique": {...},
  "explanation": "...",
  "iterations": 1
}
```

### Serve Static Files

```
GET /api/files/{path}
```

Serves rendered diagrams and page images.

## Configuration

- Upload size limit: 50 MB (configurable)
- Allowed MIME types: `application/pdf`
- CORS: Allow frontend origin

## Error Response Format

```json
{
  "error": {
    "code": "ERROR_CODE",
    "message": "Human-readable description"
  }
}
```

## Constraints

- No internal implementation details in API responses
- No raw stack traces to frontend
- All request/response schemas are Pydantic models
- API runs on port 8001 (configurable)

## Acceptance Criteria

- Health endpoint returns 200
- Document upload validates PDF and returns document_id
- Run endpoint starts background analysis and returns run_id
- SSE endpoint streams events in real-time
- Result endpoint returns complete analysis after completion
- Error responses are structured and consistent
