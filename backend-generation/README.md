# Backend Generation Pipeline (8001)

## API 구조

- `GET /health`
- `POST /api/assets/jobs/storyboard`
- `POST /api/assets/jobs/storyboard-to-video`
- `POST /api/assets/jobs` (기본: storyboard)
- `GET /api/assets/jobs/{job_id}`
- `GET /api/assets/jobs/{job_id}/result`
- `POST /api/assets/generate` (legacy wrapper, storyboard 기본)

삭제:
- `POST /api/assets/jobs/video`

## 동작 요약

### 1) storyboard
입력 대본 JSON을 정규화한 뒤 아래 순서로 생성합니다.
1. `gemini-2.5-pro`로 동적 씬 플래닝 (5씬 + character_bible + thumbnail_plan)
2. `character_anchor.png` 생성
3. 썸네일 + 프레임 5장 생성 (`gemini-3-pro-image-preview`)
4. TTS/BGM/슬라이드 영상 생성(`preview_v1.mp4`)

### 2) storyboard-to-video
`storyboard` 전 과정을 수행한 후 Veo(5초) 생성까지 실행합니다.
- 성공: `veo_v1.mp4` 반환
- 실패: storyboard 산출물은 남기고 `partial_result=true` + job failed

## 입력 정규화 지원

`script.body_15_150s`는 아래 두 형식 모두 허용합니다.
1. `{ "t": "...", "line": "..." }`
2. `{ "start_time_seconds": 15, "end_time_seconds": 45, "dialogue": "...", "speaker": "..." }`

`assets.simple_chart_or_table`도 둘 다 허용합니다.
1. 리스트형 `[{label, value}]`
2. 객체형 `{title, headers, rows}`

## 모델

- Scene planner: `SCENE_PLANNER_MODEL` (기본 `gemini-2.5-pro`)
- Image(썸네일+프레임+앵커): `GCP_VERTEX_IMAGE_MODEL` (기본 `gemini-3-pro-image-preview`)
- Video(Veo): `GCP_VERTEX_VIDEO_MODEL`
- TTS: `GCP_VERTEX_AUDIO_MODEL`

## 프롬프트 정책

- `prompt_version=storyboard_dynamic_scene_v1_ko`
- 프레임: 문자/숫자/영문/한글/자막 렌더링 금지
- 썸네일: 문자 금지, 불가피 시 숫자 `1/2/3`만 예외
- 스타일 바이블 고정 + 드리프트 금지 + 캐릭터 일관성 강제

## 출력

기본 경로: `frontend/public/generated/{job_id}/`

- `thumbnail.png`
- `character_anchor.png`
- `scene_plan.json`
- `frames/frame_01.png` ~ `frame_05.png`
- `voiceover.wav`, `bgm.wav`, `bgm.mp3`
- `preview_v1.mp4` (storyboard 영상)
- `veo_v1.mp4` (storyboard-to-video 성공 시)
- `result.json`
