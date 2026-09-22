# 04 — Model Serving Specification

## Purpose

Define how VisionOps communicates with the VLM inference server.

## Architecture

```
VisionOps Application
        ↓
  VisionModelClient (interface)
        ↓
  OpenAICompatibleVisionModelClient (implementation)
        ↓
  HTTP (OpenAI-compatible API)
        ↓
  vLLM Server
        ↓
  Qwen2.5-VL-7B-Instruct
```

The model must NOT be loaded inside the FastAPI process.

## Model Client Interface

```python
class VisionModelClient(Protocol):
    async def analyze_image(
        self,
        image: str | bytes,
        prompt: str,
        response_model: type[BaseModel] | None = None,
    ) -> str | BaseModel: ...

    async def analyze_text(
        self,
        text: str,
        prompt: str,
        response_model: type[BaseModel] | None = None,
    ) -> str | BaseModel: ...

    async def analyze_multimodal(
        self,
        images: list[str | bytes],
        text: str,
        prompt: str,
        response_model: type[BaseModel] | None = None,
    ) -> str | BaseModel: ...
```

## Configuration

```
VLLM_BASE_URL=http://localhost:8000/v1
VISION_MODEL=Qwen/Qwen2.5-VL-7B-Instruct
MODEL_TIMEOUT=120
MODEL_MAX_TOKENS=4096
```

## GPU Constraints

- ≈16 GB VRAM available
- One request at a time for V1
- Configurable: GPU memory utilization, max model length, image resolution, quantization

## vLLM Launch Configuration (Reference)

```bash
vllm serve Qwen/Qwen2.5-VL-7B-Instruct \
    --max-model-len 4096 \
    --gpu-memory-utilization 0.85 \
    --dtype auto \
    --trust-remote-code
```

## Structured Output

- VLM responses requesting structured output must include the JSON schema in the prompt
- Responses must be parsed and validated through Pydantic
- On validation failure, retry once with error feedback or return structured error

## Error Handling

| Error | Behavior |
|-------|----------|
| vLLM unreachable | Structured error, do not crash |
| Timeout | Structured error after configured timeout |
| Malformed response | Parse failure → retry once or error |
| Pydantic validation failure | Log raw response, return structured error |

## Acceptance Criteria

- Client can send image + prompt and receive response
- Client can request and validate structured JSON output
- Timeout is configurable and enforced
- vLLM unavailability returns structured error, not crash
- Model name and endpoint are configurable via env vars
