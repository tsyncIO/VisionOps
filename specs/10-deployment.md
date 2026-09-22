# 10 — Deployment Specification

## Purpose
Define how VisionOps is run locally for development and demonstration.

## Development Setup

### Prerequisites
- Python 3.12
- Node.js 18+
- uv
- GPU with ≈16 GB VRAM (for vLLM)
- Graphviz (dot)

### Backend
```bash
cd /path/to/VisionOps
uv sync
uv run uvicorn apps.api.main:app --host 0.0.0.0 --port 8001 --reload
```

### Frontend
```bash
cd apps/web
npm install
npm run dev
```

### vLLM Server
```bash
vllm serve Qwen/Qwen2.5-VL-7B-Instruct \
    --max-model-len 4096 \
    --gpu-memory-utilization 0.85 \
    --host 0.0.0.0 \
    --port 8000
```

## Environment Variables
See `.env.example`

## Ports
| Service | Port |
|---------|------|
| vLLM | 8000 |
| FastAPI | 8001 |
| Next.js | 3000 |

## Constraints
- No Kubernetes or Docker required for V1
- All services run locally
- Single machine deployment

## Acceptance Criteria
- All three services start without errors
- Frontend can reach backend
- Backend can reach vLLM (when running)
