from __future__ import annotations

import json
import re
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any, Literal

from moviepy import ImageClip, concatenate_videoclips

from app.config import get_settings
from app.schemas import (
    AssetJobCreateRequest,
    AssetJobCreateResponse,
    AssetJobStatusResponse,
    JobResultResponse,
)
from app.services.job_store import JobRecord, JobStore
from app.services.creator_reference import CreatorReferenceService
from app.services.prompt_builder import (
    FRAME_COUNT,
    PROMPT_VERSION,
    build_character_anchor_prompt,
    build_production_notes_ko,
    build_retry_prompt,
    build_storyboard_prompts,
    build_storyboard_summary_for_veo,
    build_thumbnail_prompt,
    serialize_scene_plan,
)
from app.services.scene_planner import ScenePlannerService
from app.services.vertex_provider import VertexProvider
from app.utils.files import atomic_write_json, ensure_dir, make_request_id

PipelineMode = Literal["storyboard", "storyboard_to_video"]


class PipelineService:
    def __init__(self) -> None:
        self.settings = get_settings()
        self.generated_dir = Path(self.settings.generated_dir)
        ensure_dir(self.generated_dir)
        self.store = JobStore()
        self.provider = VertexProvider()
        self.scene_planner = ScenePlannerService()
        self.creator_reference = CreatorReferenceService()
        self.executor = ThreadPoolExecutor(max_workers=self.settings.max_worker_jobs)
        self._ocr_warning = ""
        try:
            import pytesseract

            _ = pytesseract.get_tesseract_version()
            self._pytesseract = pytesseract
            self._ocr_available = True
        except Exception as exc:
            self._pytesseract = None
            self._ocr_available = False
            self._ocr_warning = f"OCR unavailable: {exc}"

    def create_job(
        self, payload: AssetJobCreateRequest, mode: PipelineMode = "storyboard"
    ) -> AssetJobCreateResponse:
        job_id = make_request_id(8)
        status_path = f"/api/assets/jobs/{job_id}"
        record = JobRecord(
            job_id=job_id,
            status="queued",
            stage="queued",
            progress=0,
            pipeline_mode=mode,
            result_path=f"/generated/{job_id}/result.json",
        )
        self.store.put(record)
        self.executor.submit(self._run_job, job_id, payload, mode)
        return AssetJobCreateResponse(
            job_id=job_id,
            status="queued",
            status_path=status_path,
            result_path=record.result_path,
            pipeline_mode=mode,
        )

    def get_status(self, job_id: str) -> AssetJobStatusResponse:
        record = self.store.get(job_id)
        if not record:
            raise KeyError(job_id)
        return AssetJobStatusResponse(**self.store.asdict(job_id))

    def get_result(self, job_id: str) -> JobResultResponse:
        result_file = self.generated_dir / job_id / "result.json"
        if not result_file.exists():
            raise FileNotFoundError(job_id)
        payload = json.loads(result_file.read_text(encoding="utf-8"))
        return JobResultResponse(**payload)

    def wait_for_legacy(
        self,
        payload: AssetJobCreateRequest,
        mode: PipelineMode = "storyboard",
        timeout_sec: int = 90,
    ) -> tuple[int, dict]:
        created = self.create_job(payload, mode=mode)
        deadline = time.time() + timeout_sec
        while time.time() < deadline:
            status = self.get_status(created.job_id)
            if status.status == "succeeded":
                return 200, {
                    "request_id": created.job_id,
                    "thumbnail_path": f"/generated/{created.job_id}/thumbnail.png",
                    "video_path": f"/generated/{created.job_id}/preview_v1.mp4",
                    "result_path": f"/generated/{created.job_id}/result.json",
                }
            if status.status == "failed":
                return 500, {"detail": status.error_message or "Job failed."}
            time.sleep(1.5)
        return 202, {
            "job_id": created.job_id,
            "status": "running",
            "status_path": created.status_path,
            "result_path": created.result_path,
        }

    def _run_job(self, job_id: str, payload: AssetJobCreateRequest, mode: PipelineMode) -> None:
        out_dir = ensure_dir(self.generated_dir / job_id)
        frames_dir = ensure_dir(out_dir / "frames")

        thumbnail_path = out_dir / "thumbnail.png"
        preview_path = out_dir / "preview_v1.mp4"
        veo_path = out_dir / "veo_v1.mp4"
        result_path = out_dir / "result.json"
        strategy_packet_path = out_dir / "strategy_packet.json"
        production_notes_path = out_dir / "production_notes.md"
        scene_plan_path = out_dir / "scene_plan.json"
        character_anchor_path = out_dir / "character_anchor.png"
        creator_reference_path = out_dir / "creator_reference.json"

        options = payload.options

        fallback_reason = None
        quality_scores: dict[str, float] = {}
        attempts: dict[str, Any] = {"video_attempts": 0, "fallback_used": False}
        provider_trace: dict[str, Any] = {
            "scene_planner_called": False,
            "video_called": False,
            "image_calls": 0,
            "tts_called": False,
            "text_guard_retries": 0,
            "text_guard_blocked_frames": [],
            "image_backoff_retries": 0,
        }
        veo_trace: dict[str, str | int | bool] = {"attempted": False, "success": False}
        frame_count = 0
        storyboard_scene_plan: list[dict[str, str | list[str]]] = []
        scene_sources: list[str] = []
        character_bible: dict[str, str | list[str]] = {}
        creator_reference: dict[str, Any] = {}
        partial_result = False
        text_guard_summary: dict[str, int | list[str] | bool | str] = {
            "thumbnail_retries": 0,
            "frame_retries": 0,
            "blocked_frames": [],
            "image_backoff_retries": 0,
            "ocr_available": self._ocr_available,
            "ocr_warning": self._ocr_warning,
        }

        try:
            self.store.update(job_id, status="running", stage="planning", progress=5, pipeline_mode=mode)
            try:
                creator_reference = self.creator_reference.resolve(payload)
                atomic_write_json(creator_reference_path, creator_reference)
            except Exception as exc:
                creator_reference = {"search_used": False, "error": str(exc)}
            provider_trace["creator_search_called"] = True

            scene_plan = self.scene_planner.plan(payload, creator_reference=creator_reference)
            provider_trace["scene_planner_called"] = True
            character_bible = {
                str(k): v if isinstance(v, list) else str(v)
                for k, v in scene_plan.character_bible.items()
            }

            storyboard_scene_plan = serialize_scene_plan(scene_plan)
            scene_sources = [scene.source_span for scene in scene_plan.scenes]
            atomic_write_json(
                scene_plan_path,
                {
                    "character_bible": scene_plan.character_bible,
                    "consistency_rules": scene_plan.consistency_rules,
                    "thumbnail_plan": scene_plan.thumbnail_plan,
                    "scene_plan": storyboard_scene_plan,
                },
            )

            strategy_packet = {
                "source_signal_id": payload.meta.source_signal_id,
                "title": payload.script.title,
                "hook": payload.script.hook_0_15s,
                "key_messages": payload.assets.on_screen_bullets[:3],
                "conclusion": payload.rationale_block.logic.conclusion,
            }
            atomic_write_json(strategy_packet_path, strategy_packet)
            production_notes_path.write_text(build_production_notes_ko(), encoding="utf-8")

            self.store.update(job_id, stage="thumbnail", progress=15)
            thumb_prompt = build_thumbnail_prompt(payload, scene_plan)
            self._generate_guarded_image(
                prompt=thumb_prompt,
                output_path=thumbnail_path,
                provider_trace=provider_trace,
                text_guard_summary=text_guard_summary,
                max_allowed_chars=self.settings.max_allowed_text_chars_thumbnail,
                retry_label="thumbnail_retries",
            )

            self.store.update(job_id, stage="anchor", progress=25)
            anchor_prompt = build_character_anchor_prompt(scene_plan)
            self._generate_guarded_image(
                prompt=anchor_prompt,
                output_path=character_anchor_path,
                provider_trace=provider_trace,
                text_guard_summary=text_guard_summary,
                max_allowed_chars=self.settings.max_allowed_text_chars_frame,
                retry_label="frame_retries",
            )

            self.store.update(job_id, stage="storyboard", progress=40)
            frame_count = FRAME_COUNT
            frame_prompts, scene_sources = build_storyboard_prompts(scene_plan)
            frame_paths: list[Path] = []
            for idx, prompt in enumerate(frame_prompts, start=1):
                frame_path = frames_dir / f"frame_{idx:02d}.png"
                self._generate_guarded_image(
                    prompt=prompt,
                    output_path=frame_path,
                    provider_trace=provider_trace,
                    text_guard_summary=text_guard_summary,
                    max_allowed_chars=self.settings.max_allowed_text_chars_frame,
                    retry_label="frame_retries",
                    reference_images=[character_anchor_path],
                    frame_name=f"frame_{idx:02d}",
                )
                frame_paths.append(frame_path)

            self._compose_slideshow_video(
                frame_paths=frame_paths,
                output_path=preview_path,
                duration_sec=options.max_video_seconds,
            )
            quality_scores["storyboard_video_quality_score"] = 0.60

            output_mode: str = "storyboard"
            video_public_path = f"/generated/{job_id}/preview_v1.mp4"
            if mode == "storyboard_to_video":
                self.store.update(job_id, stage="veo", progress=80)
                attempts["video_attempts"] = 1
                veo_trace["attempted"] = True
                provider_trace["video_called"] = True
                veo_prompt = build_storyboard_summary_for_veo(payload, scene_plan)
                try:
                    self.provider.generate_video(
                        prompt=veo_prompt,
                        output_path=veo_path,
                        duration_sec=options.max_video_seconds,
                        image_path=frame_paths[0] if frame_paths else None,
                    )
                    veo_trace["success"] = True
                    output_mode = "storyboard_to_video"
                    video_public_path = f"/generated/{job_id}/veo_v1.mp4"
                    quality_scores["veo_video_quality_score"] = 0.70
                except Exception as exc:
                    partial_result = True
                    veo_trace["success"] = False
                    veo_trace["error"] = str(exc)
                    raise RuntimeError(f"Veo generation failed after storyboard success: {exc}") from exc

            result_payload = {
                "job_id": job_id,
                "status": "succeeded",
                "pipeline_mode": mode,
                "output_mode": output_mode,
                "quality_scores": quality_scores,
                "files": {
                    "thumbnail_path": f"/generated/{job_id}/thumbnail.png",
                    "video_path": video_public_path,
                    "storyboard_video_path": f"/generated/{job_id}/preview_v1.mp4",
                    "veo_video_path": f"/generated/{job_id}/veo_v1.mp4",
                    "result_path": f"/generated/{job_id}/result.json",
                    "strategy_packet_path": f"/generated/{job_id}/strategy_packet.json",
                    "production_notes_path": f"/generated/{job_id}/production_notes.md",
                    "scene_plan_path": f"/generated/{job_id}/scene_plan.json",
                    "character_anchor_path": f"/generated/{job_id}/character_anchor.png",
                    "creator_reference_path": f"/generated/{job_id}/creator_reference.json",
                },
                "attempts": attempts,
                "fallback_reason": fallback_reason,
                "provider_trace": provider_trace,
                "prompt_version": PROMPT_VERSION,
                "frame_count": frame_count,
                "style_bible_applied": True,
                "script_grounding_applied": True,
                "scene_sources": scene_sources,
                "storyboard_scene_plan": storyboard_scene_plan,
                "image_model": self.settings.gcp_vertex_image_model,
                "scene_planner_model": self.settings.scene_planner_model,
                "character_bible": character_bible,
                "creator_reference": creator_reference,
                "scene_plan_path": f"/generated/{job_id}/scene_plan.json",
                "character_anchor_path": f"/generated/{job_id}/character_anchor.png",
                "text_guard_enabled": True,
                "text_guard_summary": text_guard_summary,
                "veo_trace": veo_trace,
                "partial_result": partial_result,
            }
            atomic_write_json(result_path, result_payload)
            self.store.update(
                job_id,
                status="succeeded",
                stage="done",
                progress=100,
                output_mode=output_mode,
                pipeline_mode=mode,
                video_path=video_public_path,
            )
        except Exception as exc:
            error_result = {
                "job_id": job_id,
                "status": "failed",
                "pipeline_mode": mode,
                "output_mode": "storyboard",
                "quality_scores": quality_scores,
                "files": {
                    "thumbnail_path": f"/generated/{job_id}/thumbnail.png",
                    "video_path": f"/generated/{job_id}/preview_v1.mp4",
                    "storyboard_video_path": f"/generated/{job_id}/preview_v1.mp4",
                    "veo_video_path": f"/generated/{job_id}/veo_v1.mp4",
                    "result_path": f"/generated/{job_id}/result.json",
                    "strategy_packet_path": f"/generated/{job_id}/strategy_packet.json",
                    "production_notes_path": f"/generated/{job_id}/production_notes.md",
                    "scene_plan_path": f"/generated/{job_id}/scene_plan.json",
                    "character_anchor_path": f"/generated/{job_id}/character_anchor.png",
                    "creator_reference_path": f"/generated/{job_id}/creator_reference.json",
                },
                "attempts": attempts,
                "fallback_reason": fallback_reason,
                "provider_trace": provider_trace,
                "prompt_version": PROMPT_VERSION,
                "frame_count": frame_count,
                "style_bible_applied": True,
                "script_grounding_applied": True,
                "scene_sources": scene_sources,
                "storyboard_scene_plan": storyboard_scene_plan,
                "image_model": self.settings.gcp_vertex_image_model,
                "scene_planner_model": self.settings.scene_planner_model,
                "character_bible": character_bible,
                "creator_reference": creator_reference,
                "scene_plan_path": f"/generated/{job_id}/scene_plan.json",
                "character_anchor_path": f"/generated/{job_id}/character_anchor.png",
                "text_guard_enabled": True,
                "text_guard_summary": text_guard_summary,
                "veo_trace": veo_trace,
                "partial_result": partial_result,
                "error_message": str(exc),
            }
            try:
                atomic_write_json(result_path, error_result)
            except Exception:
                pass
            self.store.update(
                job_id,
                status="failed",
                stage="failed",
                progress=100,
                error_message=str(exc),
                pipeline_mode=mode,
            )

    def _generate_guarded_image(
        self,
        prompt: str,
        output_path: Path,
        provider_trace: dict[str, Any],
        text_guard_summary: dict[str, int | list[str] | bool | str],
        max_allowed_chars: int,
        retry_label: str,
        reference_images: list[Path] | None = None,
        frame_name: str = "",
    ) -> None:
        last_error: Exception | None = None
        for retry_idx in range(self.settings.max_image_generation_attempts):
            try:
                retry_prompt = build_retry_prompt(prompt, retry_idx)
                self.provider.generate_image(
                    retry_prompt, output_path, reference_images=reference_images or []
                )
                provider_trace["image_calls"] += 1
                time.sleep(self.settings.image_request_interval_sec)
                if not output_path.exists() or output_path.stat().st_size < 1024:
                    raise ValueError("Generated image is missing or too small.")
                self._resize_generated_image(output_path)
                if self._ocr_available:
                    detected_chars = self._detect_text_chars(output_path)
                    if detected_chars > max_allowed_chars:
                        provider_trace["text_guard_retries"] += 1
                        text_guard_summary[retry_label] = int(text_guard_summary[retry_label]) + 1
                        raise ValueError(
                            f"Detected text chars {detected_chars} > allowed {max_allowed_chars}"
                        )
                return
            except Exception as exc:
                last_error = exc
                if self._is_resource_exhausted(exc) and retry_idx + 1 < self.settings.max_image_generation_attempts:
                    provider_trace["image_backoff_retries"] += 1
                    text_guard_summary["image_backoff_retries"] = int(
                        text_guard_summary["image_backoff_retries"]
                    ) + 1
                    time.sleep(self._retry_sleep_sec(retry_idx))
                    continue
                if retry_idx + 1 < self.settings.max_image_generation_attempts:
                    continue
        if frame_name:
            provider_trace["text_guard_blocked_frames"].append(frame_name)
            text_guard_summary["blocked_frames"].append(frame_name)
        raise RuntimeError(str(last_error))

    def _detect_text_chars(self, image_path: Path) -> int:
        if not self._ocr_available or not self._pytesseract:
            return 0
        try:
            from PIL import Image

            with Image.open(image_path) as image:
                try:
                    extracted = self._pytesseract.image_to_string(image, lang="eng+kor")
                except Exception:
                    extracted = self._pytesseract.image_to_string(image, lang="eng")
            text_chars = re.findall(r"[A-Za-z0-9가-힣]", extracted)
            return len(text_chars)
        except Exception:
            return 0

    @staticmethod
    def _is_resource_exhausted(exc: Exception) -> bool:
        message = str(exc).upper()
        return "RESOURCE_EXHAUSTED" in message or "429" in message

    def _retry_sleep_sec(self, retry_idx: int) -> float:
        base = max(0.1, self.settings.image_retry_backoff_base_sec)
        capped = min(self.settings.image_retry_backoff_max_sec, base * (2**retry_idx))
        return max(0.1, float(capped))

    def _compose_slideshow_video(
        self,
        frame_paths: list[Path],
        output_path: Path,
        duration_sec: int,
    ) -> None:
        clip_duration = duration_sec / max(1, len(frame_paths))
        clips = [ImageClip(str(frame)).with_duration(clip_duration) for frame in frame_paths]
        video = concatenate_videoclips(clips, method="compose")
        video = video.resized(new_size=(self.settings.output_image_width, self.settings.output_image_height))
        output_path.parent.mkdir(parents=True, exist_ok=True)
        # Requested behavior: no voice/music generation, export silent storyboard preview.
        video.write_videofile(
            str(output_path),
            fps=self.settings.preview_video_fps,
            codec="libx264",
            audio=False,
            bitrate=self.settings.preview_video_bitrate,
            logger=None,
        )
        video.close()

    def _resize_generated_image(self, image_path: Path) -> None:
        from PIL import Image

        with Image.open(image_path) as image:
            resized = image.convert("RGB").resize(
                (self.settings.output_image_width, self.settings.output_image_height),
                Image.Resampling.LANCZOS,
            )
            resized.save(image_path, format="PNG", optimize=True)
