# AI API Usage

Last updated: 2026-02-28

## 1) backend-strategy

### APIs used
- Google Vertex AI Generative API (via `google-genai` SDK)
- YouTube Data API v3

### Main model/API mapping
- Signal/Script generation: `STRATEGY_VERTEX_TEXT_MODEL` (current: `gemini-2.5-flash`)
- YouTube comments/channel metadata collection: `https://www.googleapis.com/youtube/v3`

### Code references
- Vertex text usage: `backend-strategy/app/services/strategy_ai_service.py`
- YouTube API usage: `backend-strategy/app/services/youtube_service.py`
- Strategy model config: `backend-strategy/app/config.py`

### Auth/config
- Vertex auth: service account file mounted as `GOOGLE_APPLICATION_CREDENTIALS`
- Project/location: `STRATEGY_GCP_PROJECT_ID`, `STRATEGY_GCP_LOCATION`
- YouTube auth: `YOUTUBE_DATA_API_KEY`

## 2) backend-generation

### APIs used
- Google Vertex AI Generative API (via `google-genai` SDK)

### Main model/API mapping
- Image generation: `GCP_VERTEX_IMAGE_MODEL` (current: `gemini-3-pro-image-preview`)
- Video generation: `GCP_VERTEX_VIDEO_MODEL` (current: `veo-3.1-generate-preview`)
- TTS generation: `GCP_VERTEX_AUDIO_MODEL` (current: `gemini-2.5-flash-preview-tts`)
- Scene planner LLM: `scene_planner_model` (default: `gemini-2.5-pro`)
- Creator reference LLM: `creator_reference_model` (default: `gemini-2.5-pro`)

### Code references
- Vertex provider (image/video/audio): `backend-generation/app/services/vertex_provider.py`
- Scene planning LLM: `backend-generation/app/services/scene_planner.py`
- Creator reference LLM: `backend-generation/app/services/creator_reference.py`
- Generation config: `backend-generation/app/config.py`

### Auth/config
- Vertex auth: service account file mounted as `GOOGLE_APPLICATION_CREDENTIALS`
- Project/location: `GENERATION_GCP_PROJECT_ID`, `GENERATION_GCP_LOCATION`

## 3) frontend (API callers)

Frontend does not call AI models directly. It calls backend APIs:
- Strategy backend: `http://localhost:8000`
- Generation backend: `http://localhost:8001`

Main call points:
- `frontend/app/page.js`
