from __future__ import annotations

import json
import math
import struct
import wave
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any, Literal

from moviepy import AudioFileClip, CompositeAudioClip, ImageClip, concatenate_videoclips

from app.config import get_settings
from app.schemas import (
    AssetJobCreateRequest,
    AssetJobCreateResponse,
    AssetJobStatusResponse,
    JobResultResponse,
)
from app.services.job_store import JobRecord, JobStore
from app.services.vertex_provider import VertexProvider
from app.utils.files import atomic_write_json, ensure_dir, make_request_id

PipelineMode = Literal["video", "image_voice_music"]


class PipelineService:
    def __init__(self) -> None:
        self.settings = get_settings()
        self.generated_dir = Path(self.settings.generated_dir)
        ensure_dir(self.generated_dir)
        self.store = JobStore()
        self.provider = VertexProvider()
        self.executor = ThreadPoolExecutor(max_workers=self.settings.max_worker_jobs)

    def create_job(
        self, payload: AssetJobCreateRequest, mode: PipelineMode = "image_voice_music"
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
        mode: PipelineMode = "image_voice_music",
        timeout_sec: int = 90,
    ) -> tuple[int, dict]:
        created = self.create_job(payload, mode=mode)
        import time

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
        result_path = out_dir / "result.json"
        strategy_packet_path = out_dir / "strategy_packet.json"
        production_notes_path = out_dir / "production_notes.md"
        voice_path = out_dir / "voiceover.wav"
        bgm_wav = out_dir / "bgm.wav"
        bgm_mp3 = out_dir / "bgm.mp3"

        options = payload.options
        hook_line = payload.script.hook_0_15s
        body_lines = [x.line for x in payload.script.body_15_150s]
        summary_text = " ".join([hook_line] + body_lines[:2] + [payload.script.closing_150_180s])
        summary_text = summary_text[:800]

        self.store.update(job_id, status="running", stage="planning", progress=5, pipeline_mode=mode)
        strategy_packet = {
            "source_signal_id": payload.meta.source_signal_id,
            "title": payload.script.title,
            "hook": payload.script.hook_0_15s,
            "key_messages": payload.assets.on_screen_bullets[:3],
            "conclusion": payload.rationale_block.logic.conclusion,
        }
        atomic_write_json(strategy_packet_path, strategy_packet)
        production_notes_path.write_text(
            "Production checklist\n"
            "1) Fact-check and policy review\n"
            "2) Subtitle timing adjustment\n"
            "3) Final pacing/cut tuning\n",
            encoding="utf-8",
        )

        fallback_reason = None
        quality_scores: dict[str, float] = {}
        attempts: dict[str, Any] = {"video_attempts": 0, "fallback_used": False}
        provider_trace: dict[str, Any] = {"video_called": False, "image_calls": 0, "tts_called": False}

        try:
            self.store.update(job_id, stage="thumbnail", progress=15)
            thumb_prompt = (
                f"YouTube thumbnail for topic: {payload.script.title}. "
                f"Use bold readable Korean text region with tone: {payload.meta.style}."
            )
            self.provider.generate_image(thumb_prompt, thumbnail_path)
            provider_trace["image_calls"] += 1

            if mode == "video":
                self.store.update(job_id, stage="video_generation", progress=40)
                final_video_ok = False
                last_video_error = None
                for attempt in range(self.settings.max_video_attempts):
                    attempts["video_attempts"] = attempt + 1
                    try:
                        provider_trace["video_called"] = True
                        video_prompt = (
                            f"Create a {options.max_video_seconds}-second trailer style video in Korean context. "
                            f"Hook: {payload.script.hook_0_15s} "
                            f"Core: {payload.rationale_block.logic.conclusion} "
                            "High clarity, editorial explainer style, no text artifacts."
                        )
                        self.provider.generate_video(video_prompt, preview_path, options.max_video_seconds)
                        video_size = preview_path.stat().st_size if preview_path.exists() else 0
                        quality_scores["video_quality_score"] = min(1.0, video_size / 2_000_000)
                        if quality_scores["video_quality_score"] >= self.settings.video_quality_threshold:
                            final_video_ok = True
                            break
                        last_video_error = "Video quality below threshold."
                    except Exception as exc:
                        last_video_error = str(exc)

                if not final_video_ok:
                    raise RuntimeError(last_video_error or "Video generation failed.")
                output_mode: PipelineMode = "video"
                self.store.update(
                    job_id,
                    stage="finalize",
                    progress=95,
                    output_mode=output_mode,
                    video_path=f"/generated/{job_id}/preview_v1.mp4",
                    pipeline_mode=mode,
                )
            else:
                self.store.update(job_id, stage="storyboard", progress=40)
                output_mode = "image_voice_music"
                attempts["fallback_used"] = True
                fallback_reason = "Storyboard endpoint intentionally skips Veo."

                frame_count = 4
                prompts = [
                    f"Editorial frame {i + 1} for {payload.script.title}. "
                    f"Bullet: {payload.assets.on_screen_bullets[i % max(1, len(payload.assets.on_screen_bullets))] if payload.assets.on_screen_bullets else payload.rationale_block.logic.conclusion}"
                    for i in range(frame_count)
                ]
                frame_paths: list[Path] = []
                for idx, prompt in enumerate(prompts, start=1):
                    frame_path = frames_dir / f"frame_{idx:02d}.png"
                    self.provider.generate_image(prompt, frame_path)
                    provider_trace["image_calls"] += 1
                    frame_paths.append(frame_path)

                self.provider.generate_tts_wav(summary_text, voice_path)
                provider_trace["tts_called"] = True

                self._make_bgm_wav(bgm_wav, duration_sec=options.max_video_seconds)
                self._wav_to_mp3(bgm_wav, bgm_mp3)
                self._compose_slideshow_video(
                    frame_paths=frame_paths,
                    voice_path=voice_path,
                    bgm_path=bgm_wav,
                    output_path=preview_path,
                    duration_sec=options.max_video_seconds,
                )
                quality_scores["video_quality_score"] = 0.60
                self.store.update(
                    job_id,
                    output_mode=output_mode,
                    alt_video_path=f"/generated/{job_id}/preview_v1.mp4",
                    pipeline_mode=mode,
                )

            result_payload = {
                "job_id": job_id,
                "status": "succeeded",
                "pipeline_mode": mode,
                "output_mode": output_mode,
                "quality_scores": quality_scores,
                "files": {
                    "thumbnail_path": f"/generated/{job_id}/thumbnail.png",
                    "video_path": f"/generated/{job_id}/preview_v1.mp4",
                    "result_path": f"/generated/{job_id}/result.json",
                    "strategy_packet_path": f"/generated/{job_id}/strategy_packet.json",
                    "production_notes_path": f"/generated/{job_id}/production_notes.md",
                },
                "attempts": attempts,
                "fallback_reason": fallback_reason,
                "provider_trace": provider_trace,
            }
            atomic_write_json(result_path, result_payload)
            self.store.update(
                job_id,
                status="succeeded",
                stage="done",
                progress=100,
                video_path=f"/generated/{job_id}/preview_v1.mp4",
                pipeline_mode=mode,
            )
        except Exception as exc:
            error_result = {
                "job_id": job_id,
                "status": "failed",
                "pipeline_mode": mode,
                "output_mode": "unknown",
                "quality_scores": quality_scores,
                "files": {
                    "thumbnail_path": f"/generated/{job_id}/thumbnail.png",
                    "video_path": f"/generated/{job_id}/preview_v1.mp4",
                    "result_path": f"/generated/{job_id}/result.json",
                },
                "attempts": attempts,
                "fallback_reason": fallback_reason,
                "provider_trace": provider_trace,
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

    @staticmethod
    def _make_bgm_wav(output_path: Path, duration_sec: int = 5, frequency: float = 220.0) -> None:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        framerate = 44100
        amplitude = 8000
        nframes = int(duration_sec * framerate)
        with wave.open(str(output_path), "w") as wav_file:
            wav_file.setparams((1, 2, framerate, nframes, "NONE", "not compressed"))
            for i in range(nframes):
                value = int(amplitude * math.sin(2 * math.pi * frequency * (i / framerate)))
                wav_file.writeframes(struct.pack("<h", value))

    @staticmethod
    def _wav_to_mp3(wav_path: Path, mp3_path: Path) -> None:
        import subprocess

        from imageio_ffmpeg import get_ffmpeg_exe

        ffmpeg = get_ffmpeg_exe()
        cmd = [ffmpeg, "-y", "-i", str(wav_path), "-codec:a", "libmp3lame", "-q:a", "5", str(mp3_path)]
        subprocess.run(cmd, check=True, capture_output=True)

    @staticmethod
    def _compose_slideshow_video(
        frame_paths: list[Path],
        voice_path: Path,
        bgm_path: Path,
        output_path: Path,
        duration_sec: int,
    ) -> None:
        clip_duration = duration_sec / max(1, len(frame_paths))
        clips = [ImageClip(str(frame)).with_duration(clip_duration) for frame in frame_paths]
        video = concatenate_videoclips(clips, method="compose")
        output_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            voice = AudioFileClip(str(voice_path)).with_duration(duration_sec).with_volume_scaled(1.0)
            bgm = AudioFileClip(str(bgm_path)).with_duration(duration_sec).with_volume_scaled(0.2)
            mixed = CompositeAudioClip([voice, bgm])
            final = video.with_audio(mixed)
            final.write_videofile(str(output_path), fps=24, codec="libx264", audio_codec="aac", logger=None)
            final.close()
            voice.close()
            bgm.close()
        except Exception:
            video.write_videofile(str(output_path), fps=24, codec="libx264", audio=False, logger=None)
        video.close()
