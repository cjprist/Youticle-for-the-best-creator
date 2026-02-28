# Backend-Generation Storyboard API Test Report

Date: 2026-02-28
Scope: `backend-generation` only

## 1) Implemented API split

- `POST /api/assets/jobs/video`
  - Veo 5-second path
- `POST /api/assets/jobs/storyboard`
  - Image + Voice + Music path
  - Veo is skipped by design
- `POST /api/assets/jobs`
  - Defaults to storyboard mode (cost-safe)
- `GET /api/assets/jobs/{job_id}`
- `GET /api/assets/jobs/{job_id}/result`
- `POST /api/assets/generate`
  - Legacy wrapper mapped to storyboard mode

## 2) Requirements/Dockerfile updates

### requirements.txt
- `google-genai==1.40.0`
- `pillow==10.4.0`
- `moviepy==2.1.2`
- `imageio-ffmpeg==0.6.0`

### Dockerfile
- Added system package install for runtime media processing:
  - `ffmpeg`
- Existing app copy/start command kept

## 3) Real storyboard API call test (local runtime)

Test command path:
- sample payload: `backend-generation/examples/sample_script.json`
- endpoint: `POST /api/assets/jobs/storyboard`

Observed result:
- create status: `200`
- final status: `succeeded`
- pipeline mode: `image_voice_music`
- output mode: `image_voice_music`
- provider trace:
  - `video_called: false`
  - `image_calls: 5`
  - `tts_called: true`

Generated files confirmed:
- `thumbnail.png`
- `preview_v1.mp4`
- `voiceover.wav`
- `bgm.mp3`
- `result.json`
- `strategy_packet.json`
- `production_notes.md`

## 4) Docker execution test status

Attempted command:

```bash
docker compose up --build -d backend-generation
```

Result in this execution environment:
- Failed because Docker CLI is not installed/available:
  - `docker : The term 'docker' is not recognized ...`

Conclusion:
- Docker-based runtime test is **blocked by host environment**, not by code.
- Run the same command on a host with Docker Desktop/CLI enabled.

## 5) Frontend experience plan (single cohesive storyboard experience)

Goal: Let users consume storyboard output as one continuous experience, not as separate files.

### A. Data contract from backend
- Poll `GET /api/assets/jobs/{job_id}` until `succeeded`
- Read `result.json` and use:
  - `files.thumbnail_path`
  - `files.video_path` (`preview_v1.mp4`)
  - optional: `strategy_packet.json`, `production_notes.md`

### B. One-screen player composition
- Hero area:
  - autoplay muted `preview_v1.mp4`
  - overlay title from strategy packet
- Timeline panel:
  - show generated key points + rationale summary
- Creator actions:
  - `Use as base draft`
  - `Regenerate storyboard`
  - `Send to edit queue`

### C. UX flow
1. User submits generation request
2. Progress view (queued/running/stage/progress)
3. On success, switch to storyboard player view
4. Offer downloadable package links:
   - video, audio, notes, strategy packet

### D. Recommended frontend checks
- If `pipeline_mode=image_voice_music`:
  - show “Storyboard (No Veo)” badge
- If `provider_trace.video_called=true`:
  - show “Video Mode” badge
- If `failed`:
  - expose `error_message` and retry CTA

