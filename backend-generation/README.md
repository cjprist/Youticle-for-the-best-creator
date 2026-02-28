# Backend Generation Pipeline (8001)

Real Vertex pipeline:
1) Try 5-second video generation
2) If quality is below threshold, fallback to image+voice+music composition

## Endpoints

- `GET /health`
- `POST /api/assets/jobs/video`
- `POST /api/assets/jobs/storyboard`
- `POST /api/assets/jobs` (defaults to storyboard mode)
- `GET /api/assets/jobs/{job_id}`
- `GET /api/assets/jobs/{job_id}/result`
- `POST /api/assets/generate` (legacy wrapper)

## Quick Start

Create job:

```bash
curl -X POST http://localhost:8001/api/assets/jobs/storyboard \
  -H "Content-Type: application/json" \
  -d @backend-generation/examples/sample_script.json
```

Poll:

```bash
curl http://localhost:8001/api/assets/jobs/<job_id>
```

## Outputs

Files are written under:

- `frontend/public/generated/{job_id}/thumbnail.png`
- `frontend/public/generated/{job_id}/preview_v1.mp4`
- `frontend/public/generated/{job_id}/result.json`

`result.json` includes:
- `pipeline_mode` (`video` or `image_voice_music`)
- `provider_trace` (whether Veo was called, image/tts call counts)
