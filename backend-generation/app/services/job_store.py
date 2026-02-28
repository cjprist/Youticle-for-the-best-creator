from __future__ import annotations

from dataclasses import asdict, dataclass, field
from threading import Lock
from typing import Literal


@dataclass
class JobRecord:
    job_id: str
    status: Literal["queued", "running", "succeeded", "failed"] = "queued"
    stage: str = "queued"
    progress: int = 0
    pipeline_mode: Literal["video", "image_voice_music", "unknown"] = "unknown"
    output_mode: Literal["video", "image_voice_music", "unknown"] = "unknown"
    video_path: str | None = None
    alt_video_path: str | None = None
    result_path: str = ""
    error_message: str | None = None


class JobStore:
    def __init__(self) -> None:
        self._lock = Lock()
        self._jobs: dict[str, JobRecord] = {}

    def put(self, record: JobRecord) -> None:
        with self._lock:
            self._jobs[record.job_id] = record

    def get(self, job_id: str) -> JobRecord | None:
        with self._lock:
            return self._jobs.get(job_id)

    def update(self, job_id: str, **fields: object) -> JobRecord:
        with self._lock:
            if job_id not in self._jobs:
                raise KeyError(job_id)
            record = self._jobs[job_id]
            for key, value in fields.items():
                setattr(record, key, value)
            return record

    def asdict(self, job_id: str) -> dict:
        with self._lock:
            record = self._jobs[job_id]
            return asdict(record)
