"use client";

import { useState } from "react";

import ChannelHandleForm from "./components/channel-handle-form";

const strategyApi = process.env.NEXT_PUBLIC_STRATEGY_API_URL || "http://localhost:8000";

async function fetchYouTubeComments(channelHandle, maxVideos) {
  const response = await fetch(`${strategyApi}/api/v1/strategy/youtube/comments`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      channel_handle: channelHandle,
      max_videos: maxVideos,
      max_comments_per_video: 10,
    }),
  });

  if (!response.ok) {
    let detail = "요청 처리 중 오류가 발생했습니다.";
    try {
      const payload = await response.json();
      detail = payload.detail || detail;
    } catch {}
    throw new Error(detail);
  }

  return response.json();
}

function mapCommentsToSignalVideos(commentResponse) {
  return (commentResponse.videos || []).map((video) => ({
    video_id: video.video_id,
    title: video.video_title || null,
    thumbnail_url: video.thumbnail_url || null,
    published_at: video.published_at || null,
    comments: (video.comments || []).map((comment) => ({
      author: comment.author || null,
      text: comment.text,
      published_at: comment.published_at || null,
      like_count: comment.like_count || 0,
    })),
    comment_error: null,
  }));
}

async function generateSignalOutput(videos) {
  const response = await fetch(`${strategyApi}/api/v1/strategy/signals/from-comments`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      language: "ko",
      videos,
      filters: {
        min_like: 0,
        topk_per_video: 50,
        exclude_meme: true,
        exclude_thumbnail_meta: true,
        exclude_pure_praise: true,
        dedupe: "semantic",
      },
    }),
  });

  if (!response.ok) {
    let detail = "Signal 생성 중 오류가 발생했습니다.";
    try {
      const payload = await response.json();
      detail = payload.detail || detail;
    } catch {}
    throw new Error(detail);
  }

  return response.json();
}

async function generateScriptOutput(signal) {
  const signalId = signal?.signal_id;
  if (!signalId) throw new Error("선택된 signal_id가 없습니다.");

  const response = await fetch(`${strategyApi}/api/v1/strategy/scripts/from-signal`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      signal,
      signal_id: signalId,
      language: "ko",
      target_length_sec: 180,
      style: "informative",
    }),
  });

  if (!response.ok) {
    let detail = "Script 생성 중 오류가 발생했습니다.";
    try {
      const payload = await response.json();
      detail = payload.detail || detail;
    } catch {}
    throw new Error(detail);
  }

  return response.json();
}

function normalizeText(text) {
  return typeof text === "string" ? text.trim() : "";
}

function splitSentences(text) {
  const normalized = normalizeText(text);
  if (!normalized) return [];

  if (normalized.includes("\n")) {
    return normalized
      .split("\n")
      .map((line) => line.trim())
      .filter(Boolean);
  }

  return normalized
    .split(/(?<=[.!?])\s+/)
    .map((line) => line.trim())
    .filter(Boolean);
}

function toTextList(value) {
  if (Array.isArray(value)) {
    return value
      .map((item) => {
        if (typeof item === "string") return item.trim();
        if (item && typeof item === "object" && typeof item.text === "string") {
          return item.text.trim();
        }
        return "";
      })
      .filter(Boolean);
  }

  if (typeof value === "string") {
    return splitSentences(value);
  }

  return [];
}

function toContentPlanList(value) {
  if (Array.isArray(value) || typeof value === "string") {
    return toTextList(value);
  }

  if (value && typeof value === "object") {
    const orderedKeys = ["short_term", "mid_term", "long_term"];
    const entries = [];

    orderedKeys.forEach((key) => {
      if (typeof value[key] === "string" && value[key].trim()) {
        const label = key.replace("_", " ");
        entries.push(`${label}: ${value[key].trim()}`);
      }
    });

    Object.entries(value).forEach(([key, raw]) => {
      if (orderedKeys.includes(key)) return;
      if (typeof raw !== "string" || !raw.trim()) return;
      entries.push(`${key}: ${raw.trim()}`);
    });

    return entries;
  }

  return [];
}

function toTradeoffList(value) {
  if (!Array.isArray(value)) return [];
  return value
    .map((item) => {
      if (typeof item === "string") return item;
      if (item && typeof item === "object") {
        const left = item.left || item.a || item.option_a;
        const right = item.right || item.b || item.option_b;
        const note = item.note || item.description || "";
        if (left && right) return `${left} vs ${right}${note ? ` - ${note}` : ""}`;
        if (note) return note;
      }
      return "";
    })
    .filter(Boolean);
}

function getSignalFields(signal) {
  const evidence = signal?.evidence || {};
  const aggregate = evidence?.aggregate || {};
  const insight = signal?.insight || {};
  const contentBlueprint = signal?.content_blueprint || {};
  const framework = contentBlueprint?.framework_or_tool || {};
  const causalModel = signal?.causal_model || {};
  const confidence = signal?.confidence || {};
  const sourceVideosFromSignal = Array.isArray(signal?.source_videos) ? signal.source_videos : [];

  return {
    demandStatement: signal?.demand_statement || signal?.demand?.one_liner || signal?.demand || "-",
    observations: toTextList(signal?.observations || causalModel?.observations),
    supportingComments: Array.isArray(evidence?.supporting_comments)
      ? evidence.supporting_comments
      : Array.isArray(signal?.supporting_comments)
        ? signal.supporting_comments
        : [],
    sourceVideos: sourceVideosFromSignal,
    excludedExamples: Array.isArray(evidence?.excluded_examples)
      ? evidence.excluded_examples
      : Array.isArray(signal?.excluded_examples)
        ? signal.excluded_examples
        : [],
    evidenceAggregate: {
      evidenceStrength: aggregate?.evidence_strength ?? null,
      coverageVideos: aggregate?.coverage_videos ?? null,
      recurrenceScore: aggregate?.recurrence_score ?? null,
      topLikeCount: aggregate?.top_like_count ?? null,
    },
    inferenceSteps: toTextList(signal?.inference_steps || causalModel?.inference_steps),
    rootCauseHypothesis:
      insight?.root_cause_hypothesis ||
      signal?.root_cause_hypothesis ||
      causalModel?.root_cause_hypothesis ||
      "-",
    keyTradeoffs: toTradeoffList(insight?.key_tradeoffs),
    misconceptionsToCorrect: toTextList(insight?.misconceptions_to_correct),
    explanation: signal?.explanation || confidence?.explanation || "-",
    actionables: toTextList(signal?.actionables),
    contentPlan: toContentPlanList(signal?.content_plan),
    coreQuestion: signal?.core_question || "-",
    hook: contentBlueprint?.hook || "-",
    outline: toTextList(contentBlueprint?.outline),
    frameworkName: framework?.name || "-",
    frameworkSteps: toTextList(framework?.steps),
    whyNow: signal?.why_now || "-",
    confidenceScore: typeof confidence?.score === "number" ? confidence.score : null,
  };
}

function valueOrDash(value) {
  if (value === null || value === undefined || value === "") return "-";
  return value;
}

function extractSegmentText(segment) {
  if (!segment) return "-";
  if (typeof segment === "string") return segment;
  if (typeof segment === "object") {
    if (typeof segment.dialogue === "string" && segment.dialogue.trim()) return segment.dialogue;
    if (typeof segment.text === "string" && segment.text.trim()) return segment.text;
  }
  return "-";
}

function formatTimeRange(part) {
  if (!part || typeof part !== "object") return "-";
  if (typeof part.time_range === "string" && part.time_range.trim()) return part.time_range;

  const start = part.start_time_seconds;
  const end = part.end_time_seconds;
  if (typeof start === "number" && typeof end === "number") {
    return `${start}-${end}s`;
  }
  if (typeof start === "number") return `${start}s-`;
  if (typeof end === "number") return `-${end}s`;
  return "-";
}

export default function Home() {
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isGeneratingScript, setIsGeneratingScript] = useState(false);
  const [errorMessage, setErrorMessage] = useState("");
  const [result, setResult] = useState(null);

  async function handleSubmit({ channelHandle, maxVideos }) {
    setIsSubmitting(true);
    setErrorMessage("");
    setResult(null);

    try {
      const commentData = await fetchYouTubeComments(channelHandle, maxVideos);
      const signalVideos = mapCommentsToSignalVideos(commentData);
      const signalOutput = await generateSignalOutput(signalVideos);
      const firstSignal = signalOutput?.signals?.[0] || null;

      setResult({
        channel_handle: commentData.channel_handle,
        channel_id: commentData.channel_id,
        channel_name: commentData.channel_name,
        channel_thumbnail_url: commentData.channel_thumbnail_url,
        subscriber_count: commentData.subscriber_count,
        video_count: commentData.video_count,
        signal_output: signalOutput,
        selected_signal: firstSignal,
        script_output: null,
      });
    } catch (error) {
      setErrorMessage(error.message);
    } finally {
      setIsSubmitting(false);
    }
  }

  async function handleGenerateScript() {
    if (!result?.selected_signal?.signal_id) {
      setErrorMessage("유효한 Signal이 없어 대본을 생성할 수 없습니다.");
      return;
    }

    setIsGeneratingScript(true);
    setErrorMessage("");
    try {
      const scriptOutput = await generateScriptOutput(result.selected_signal);
      setResult((prev) => ({ ...prev, script_output: scriptOutput }));
    } catch (error) {
      setErrorMessage(error.message);
    } finally {
      setIsGeneratingScript(false);
    }
  }

  function handleSelectSignal(signalId) {
    setResult((prev) => {
      if (!prev?.signal_output?.signals?.length) return prev;
      const selectedSignal =
        prev.signal_output.signals.find((signal) => signal.signal_id === signalId) || null;
      return { ...prev, selected_signal: selectedSignal, script_output: null };
    });
  }

  const signalList = result?.signal_output?.signals || [];
  const signalDetail = result?.selected_signal ? getSignalFields(result.selected_signal) : null;
  const sourceVideos =
    signalDetail?.sourceVideos?.length > 0
      ? signalDetail.sourceVideos
      : (signalDetail?.supportingComments || [])
          .map((comment) => ({
            video_id: comment?.video_id,
            video_title: comment?.video_title,
            thumbnail_url: comment?.thumbnail_url,
            video_published_at: comment?.video_published_at,
          }))
          .filter((video) => Boolean(video.video_id))
          .filter(
            (video, index, arr) =>
              arr.findIndex((item) => item.video_id === video.video_id) === index
          );

  return (
    <main className="page-shell">
      <section className="hero">
        <p className="eyebrow">Youticle for the best creator</p>
        <h1>댓글에서 기회를 읽고, 다음 히트를 설계하다</h1>
        <p className="lead">
          신호 분석은 근거(댓글) → 해석(인과) → 결론(콘텐츠 설계) 흐름으로 보여주고, 선택한 Signal로
          바로 대본을 생성합니다.
        </p>
      </section>

      <section className="grid">
        <article className="card card-large">
          <h2>1) 채널 입력</h2>
          <ChannelHandleForm onSubmit={handleSubmit} isSubmitting={isSubmitting} />
          {errorMessage ? <p className="request-error">오류: {errorMessage}</p> : null}
        </article>

        <article className="card">
          <h2>진행 상태</h2>
          {result ? (
            <div className="result-block">
              <p>채널 핸들: {result.channel_handle}</p>
              <p>채널명: {result.channel_name || "-"}</p>
              <p>채널 ID: {result.channel_id}</p>
              <p>구독자수: {typeof result.subscriber_count === "number" ? result.subscriber_count.toLocaleString() : "-"}</p>
              {result.channel_thumbnail_url ? (
                <img
                  src={result.channel_thumbnail_url}
                  alt={`${result.channel_name || result.channel_handle} channel thumbnail`}
                  className="channel-thumb"
                />
              ) : null}
              <p>분석 영상 수: {result.video_count}</p>
              <p>생성 Signal 수: {signalList.length}</p>
              <p>선택 Signal: {result.selected_signal?.signal_id ?? "(없음)"}</p>
              <p>생성 대본 제목: {result.script_output?.script?.title ?? "(아직 생성 전)"}</p>
            </div>
          ) : (
            <p className="muted">아직 요청 결과가 없습니다.</p>
          )}
        </article>
      </section>

      {result?.selected_signal && signalDetail ? (
        <section className="signal-workspace">
          <h2>2) Signal 분석 워크스페이스</h2>
          <div className="signal-layout">
            <aside className="signal-sidebar">
              <h3>Signals</h3>
              <div className="signal-list">
                {signalList.map((signal) => (
                  <button
                    key={signal.signal_id}
                    type="button"
                    className={`signal-list-item ${
                      result.selected_signal?.signal_id === signal.signal_id ? "is-active" : ""
                    }`}
                    onClick={() => handleSelectSignal(signal.signal_id)}
                  >
                    <p className="signal-id">{signal.signal_id}</p>
                    <p className="signal-title">{signal.title || "Untitled Signal"}</p>
                    <p className="signal-meta">
                      confidence: {valueOrDash(signal?.confidence?.score)}
                    </p>
                  </button>
                ))}
              </div>
            </aside>

            <div className="signal-main">
              <section className="signal-stage">
                <h3>1) 결론 (Decision)</h3>
                <p className="decision-question">Q. {signalDetail.coreQuestion}</p>
                <div className="decision-blueprint">
                  <p>
                    <strong>시청자 댓글 피드백:</strong> {signalDetail.demandStatement}
                  </p>
                  <h4 className="subheading">다음 영상 전략</h4>
                  {signalDetail.actionables.length > 0 ? (
                    <ul className="analysis-list">
                      {signalDetail.actionables.map((item, index) => (
                        <li key={`actionable-${index}`}>{item}</li>
                      ))}
                    </ul>
                  ) : (
                    <p className="muted">actionables 없음</p>
                  )}
                  <h4 className="subheading">다음 영상 TODO</h4>
                  {signalDetail.contentPlan.length > 0 ? (
                    <ul className="analysis-list">
                      {signalDetail.contentPlan.map((item, index) => (
                        <li key={`content-plan-${index}`}>{item}</li>
                      ))}
                    </ul>
                  ) : (
                    <p className="muted">content_plan 없음</p>
                  )}
                </div>
              </section>

              <section className="signal-stage">
                <h3>2) 근거 (Observed)</h3>
                <h4 className="subheading">근거 영상</h4>
                {sourceVideos.length > 0 ? (
                  <ul className="video-evidence-list">
                    {sourceVideos.map((video, index) => (
                      <li key={`${video.video_id || "video"}-${index}`} className="video-evidence-item">
                        {video.thumbnail_url ? (
                          <img
                            src={video.thumbnail_url}
                            alt={video.video_title || video.video_id || "video thumbnail"}
                            className="video-evidence-thumb"
                          />
                        ) : null}
                        <p className="video-evidence-title">{video.video_title || "(제목 없음)"}</p>
                        <p className="video-evidence-meta">
                          {video.video_id}
                          {video.video_published_at ? ` / ${video.video_published_at}` : ""}
                        </p>
                      </li>
                    ))}
                  </ul>
                ) : (
                  <p className="muted">근거 영상 정보 없음</p>
                )}
                <div className="aggregate-strip">
                  <span>evidence_strength: {valueOrDash(signalDetail.evidenceAggregate.evidenceStrength)}</span>
                  <span>coverage_videos: {valueOrDash(signalDetail.evidenceAggregate.coverageVideos)}</span>
                  <span>recurrence_score: {valueOrDash(signalDetail.evidenceAggregate.recurrenceScore)}</span>
                  <span>top_like_count: {valueOrDash(signalDetail.evidenceAggregate.topLikeCount)}</span>
                </div>
                {signalDetail.observations.length > 0 ? (
                  <ul className="analysis-list">
                    {signalDetail.observations.map((item, index) => (
                      <li key={`obs-${index}`}>{item}</li>
                    ))}
                  </ul>
                ) : null}
                <h4 className="subheading">Supporting Comments</h4>
                {signalDetail.supportingComments.length > 0 ? (
                  <ul className="comment-list">
                    {signalDetail.supportingComments.map((comment, index) => (
                      <li key={`support-${index}`} className="comment-item">
                        <p className="comment-text">{comment?.text || comment?.comment_text || "-"}</p>
                        <p className="comment-meta">
                          {comment?.author || "작성자 미상"} / likes: {comment?.like_count ?? 0} / video:{" "}
                          {comment?.video_id || "-"}
                        </p>
                      </li>
                    ))}
                  </ul>
                ) : (
                  <p className="muted">근거 댓글 없음</p>
                )}
                <details className="excluded-box">
                  <summary>제외된 댓글 보기</summary>
                  {signalDetail.excludedExamples.length > 0 ? (
                    <pre className="json-preview">
                      {JSON.stringify(signalDetail.excludedExamples, null, 2)}
                    </pre>
                  ) : (
                    <p className="muted">제외된 댓글 없음</p>
                  )}
                </details>
              </section>

              <section className="signal-stage">
                <h3>3) 해석 (Interpretation)</h3>
                {signalDetail.inferenceSteps.length > 0 ? (
                  <ol className="analysis-list ordered">
                    {signalDetail.inferenceSteps.map((item, index) => (
                      <li key={`infer-${index}`}>{item}</li>
                    ))}
                  </ol>
                ) : (
                  <p className="muted">inference_steps 없음</p>
                )}
                <div className="interpretation-box">
                  <p>
                    <strong>Root Cause Hypothesis:</strong> {signalDetail.rootCauseHypothesis}
                  </p>
                  <p>
                    <strong>Explanation:</strong> {signalDetail.explanation}
                  </p>
                </div>
                <h4 className="subheading">Key Tradeoffs</h4>
                {signalDetail.keyTradeoffs.length > 0 ? (
                  <ul className="analysis-list">
                    {signalDetail.keyTradeoffs.map((item, index) => (
                      <li key={`tradeoff-${index}`}>{item}</li>
                    ))}
                  </ul>
                ) : (
                  <p className="muted">tradeoff 없음</p>
                )}
                <h4 className="subheading">Misconceptions to Correct</h4>
                {signalDetail.misconceptionsToCorrect.length > 0 ? (
                  <ul className="analysis-list">
                    {signalDetail.misconceptionsToCorrect.map((item, index) => (
                      <li key={`misconception-${index}`}>{item}</li>
                    ))}
                  </ul>
                ) : (
                  <p className="muted">교정할 오해 없음</p>
                )}
              </section>

              <div className="signal-actionbar">
                <div>
                  <p className="action-title">선택 Signal로 대본 생성</p>
                  <p className="action-meta">
                    signal_id: {result.selected_signal.signal_id} / target: 180s / style: informative
                  </p>
                </div>
                <button
                  type="button"
                  className="primary-btn"
                  onClick={handleGenerateScript}
                  disabled={isGeneratingScript}
                >
                  {isGeneratingScript ? "대본 생성 중..." : "🎬 대본 생성"}
                </button>
              </div>

              {result.script_output ? (
                <section className="result-panel">
                  <h3>🎬 생성된 영상 대본</h3>
                  <p>
                    <strong>제목:</strong>{" "}
                    {result.script_output?.script?.title || result.script_output?.meta?.title || "-"}
                  </p>
                  <p>
                    <strong>Hook:</strong>{" "}
                    {extractSegmentText(result.script_output?.script?.hook_0_15s)}
                  </p>
                  <p>
                    <strong>결론 + CTA:</strong>{" "}
                    {extractSegmentText(result.script_output?.script?.closing_150_180s)}
                  </p>
                  {Array.isArray(result.script_output?.script?.body_15_150s) &&
                  result.script_output.script.body_15_150s.length > 0 ? (
                    <div>
                      <h4 className="subheading">본문 타임라인</h4>
                      <ul className="analysis-list">
                        {result.script_output.script.body_15_150s.map((part, index) => (
                          <li key={`body-part-${index}`}>
                            [{formatTimeRange(part)}] {extractSegmentText(part)}
                          </li>
                        ))}
                      </ul>
                    </div>
                  ) : null}
                  <details>
                    <summary>대본 JSON 보기</summary>
                    <pre className="json-preview">{JSON.stringify(result.script_output, null, 2)}</pre>
                  </details>
                </section>
              ) : null}
            </div>
          </div>
        </section>
      ) : null}
    </main>
  );
}
