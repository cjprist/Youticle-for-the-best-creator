# Storyboard / Storyboard-to-Video Test Report

## Scope

- API: `POST /api/assets/jobs/storyboard`
- API: `POST /api/assets/jobs/storyboard-to-video`
- Input: `backend-generation/examples/sample_script_3.json`
- Prompt version: `storyboard_dynamic_scene_v1_ko`
- Scene planner model: `gemini-2.5-pro`
- Image model: `gemini-3-pro-image-preview`

## Checklist

1. 입력 정규화: `dialogue/start_time_seconds` 형식 파싱 성공
2. 동적 씬 플래너: scene 5개 + character_bible 생성
3. 캐릭터 앵커: `character_anchor.png` 생성
4. storyboard 프레임: `frame_01~05.png` 생성
5. result 메타:
   - `scene_planner_model`
   - `character_bible`
   - `scene_plan_path`
   - `character_anchor_path`
   - `veo_trace`
   - `partial_result`
6. `storyboard-to-video`에서 Veo 성공 시 `veo_v1.mp4` 생성
7. Veo 실패 시 job failed + `partial_result=true` + storyboard 산출물 유지

## Notes

- OCR 미설치 환경에서는 텍스트 가드는 프롬프트/재시도 중심으로 동작하고 `text_guard_summary.ocr_warning`에 기록됩니다.
- `POST /api/assets/jobs/video`는 제거되어야 하며 호출 시 404/405/410 중 하나가 정상입니다.
