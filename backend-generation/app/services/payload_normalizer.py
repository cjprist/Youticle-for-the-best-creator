from __future__ import annotations

from typing import Any

from app.schemas import (
    AssetJobCreateRequest,
    AssetsBlock,
    BodyLine,
    ChartItem,
    CtaBlock,
    ExcludedItem,
    JobOptions,
    LogicBlock,
    MetaData,
    RationaleBlock,
    ScriptBlock,
)


def _as_str(value: Any, default: str = "") -> str:
    if value is None:
        return default
    text = str(value).strip()
    return text if text else default


def _normalize_time_window(item: dict[str, Any]) -> str:
    t_value = _as_str(item.get("t"))
    if t_value:
        return t_value
    start = item.get("start_time_seconds")
    end = item.get("end_time_seconds")
    if start is None and end is None:
        return ""
    return f"{start}-{end}s"


def _normalize_body_lines(raw_script: dict[str, Any]) -> list[BodyLine]:
    body = raw_script.get("body_15_150s", [])
    lines: list[BodyLine] = []
    if not isinstance(body, list):
        return lines
    for item in body:
        if not isinstance(item, dict):
            continue
        line = _as_str(item.get("line")) or _as_str(item.get("dialogue"))
        if not line:
            continue
        lines.append(BodyLine(t=_normalize_time_window(item), line=line))
    return lines


def _normalize_what_we_excluded(raw: Any) -> list[ExcludedItem]:
    if isinstance(raw, list):
        out: list[ExcludedItem] = []
        for item in raw:
            if not isinstance(item, dict):
                continue
            example = _as_str(item.get("example"))
            reason = _as_str(item.get("reason"))
            if example and reason:
                out.append(ExcludedItem(example=example, reason=reason))
        return out
    if isinstance(raw, str) and raw.strip():
        return [ExcludedItem(example=raw.strip(), reason="normalized_from_string")]
    return []


def _normalize_chart_items(raw_assets: dict[str, Any]) -> list[ChartItem]:
    chart = raw_assets.get("simple_chart_or_table", [])
    if isinstance(chart, list):
        out: list[ChartItem] = []
        for item in chart:
            if not isinstance(item, dict):
                continue
            label = _as_str(item.get("label"))
            value = _as_str(item.get("value"))
            if label and value:
                out.append(ChartItem(label=label, value=value))
        return out

    if isinstance(chart, dict):
        rows = chart.get("rows", [])
        out: list[ChartItem] = []
        if isinstance(rows, list):
            for row in rows:
                if isinstance(row, list) and len(row) >= 2:
                    label = _as_str(row[0])
                    value = _as_str(row[1])
                    if label and value:
                        out.append(ChartItem(label=label, value=value))
        return out

    return []


def normalize_asset_job_payload(raw: dict[str, Any]) -> AssetJobCreateRequest:
    if not isinstance(raw, dict):
        raise ValueError("Payload must be a JSON object.")

    raw_meta = raw.get("meta", {}) if isinstance(raw.get("meta"), dict) else {}
    raw_script = raw.get("script", {}) if isinstance(raw.get("script"), dict) else {}
    raw_rationale = (
        raw.get("rationale_block", {}) if isinstance(raw.get("rationale_block"), dict) else {}
    )
    raw_assets = raw.get("assets", {}) if isinstance(raw.get("assets"), dict) else {}
    raw_options = raw.get("options", {}) if isinstance(raw.get("options"), dict) else {}

    meta = MetaData(
        source_signal_id=_as_str(raw_meta.get("source_signal_id"), "unknown_signal"),
        target_length_sec=int(raw_meta.get("target_length_sec", 180)),
        language=_as_str(raw_meta.get("language"), "ko"),
        style=_as_str(raw_meta.get("style"), "informative"),
        title=_as_str(raw_meta.get("title")),
        description=_as_str(raw_meta.get("description")),
        target_audience=_as_str(raw_meta.get("target_audience")),
    )

    if "logic" in raw_rationale and isinstance(raw_rationale.get("logic"), dict):
        raw_logic = raw_rationale["logic"]
        logic = LogicBlock(
            observations=raw_logic.get("observations", []) or [],
            inference=raw_logic.get("inference", []) or [],
            conclusion=_as_str(raw_logic.get("conclusion")),
        )
    else:
        logic = LogicBlock(
            observations=raw_rationale.get("observations", []) or [],
            inference=raw_rationale.get("inference", []) or [],
            conclusion=_as_str(raw_rationale.get("conclusion")),
        )

    rationale = RationaleBlock(
        title=_as_str(raw_rationale.get("title")),
        evidence_summary=raw_rationale.get("evidence_summary", []) or [],
        logic=logic,
        what_we_excluded=_normalize_what_we_excluded(raw_rationale.get("what_we_excluded")),
    )

    title = _as_str(raw_script.get("title")) or meta.title or "제목 미지정"
    body_lines = _normalize_body_lines(raw_script)
    if not body_lines:
        fallback_line = _as_str(logic.conclusion, _as_str(raw_script.get("hook_0_15s"), "핵심 요약"))
        body_lines = [BodyLine(t="", line=fallback_line)]

    script = ScriptBlock(
        title=title,
        hook_0_15s=_as_str(raw_script.get("hook_0_15s"), logic.conclusion),
        body_15_150s=body_lines,
        closing_150_180s=_as_str(raw_script.get("closing_150_180s"), logic.conclusion),
        cta=CtaBlock.model_validate(raw_script.get("cta", {}) or {}),
    )

    bullets = raw_assets.get("on_screen_bullets", [])
    if not isinstance(bullets, list):
        bullets = []
    assets = AssetsBlock(
        on_screen_bullets=[_as_str(item) for item in bullets if _as_str(item)],
        simple_chart_or_table=_normalize_chart_items(raw_assets),
        disclaimer=_as_str(raw_assets.get("disclaimer")),
    )

    options = JobOptions.model_validate(raw_options or {})

    return AssetJobCreateRequest(
        meta=meta,
        rationale_block=rationale,
        script=script,
        assets=assets,
        options=options,
    )
