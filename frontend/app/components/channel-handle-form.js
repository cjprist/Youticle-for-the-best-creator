"use client";

import { useMemo, useState } from "react";

const HANDLE_PATTERN = /^@[A-Za-z0-9._-]{3,30}$/;

function isYouTubeHost(hostname) {
  return hostname === "youtube.com" || hostname.endsWith(".youtube.com");
}

function parseChannelHandle(rawValue) {
  const value = rawValue.trim();
  if (!value) return "";

  if (value.startsWith("@")) {
    return value;
  }

  const normalizedUrl = /^https?:\/\//i.test(value) ? value : `https://${value}`;

  try {
    const url = new URL(normalizedUrl);
    if (!isYouTubeHost(url.hostname)) {
      return "";
    }

    const handlePath = url.pathname
      .split("/")
      .find((chunk) => chunk.startsWith("@"));

    return handlePath || "";
  } catch {
    return "";
  }
}

export default function ChannelHandleForm({ onSubmit, isSubmitting }) {
  const [inputValue, setInputValue] = useState("");
  const [error, setError] = useState("");

  const normalizedHandle = useMemo(
    () => parseChannelHandle(inputValue),
    [inputValue]
  );

  const hasValidHandle = HANDLE_PATTERN.test(normalizedHandle);

  async function handleSubmit(event) {
    event.preventDefault();

    if (!hasValidHandle) {
      setError("유효한 핸들을 입력해주세요. 예: @creators");
      return;
    }

    setError("");
    await onSubmit({
      channelHandle: normalizedHandle,
      maxVideos: 2,
    });
  }

  return (
    <form className="handle-form" onSubmit={handleSubmit}>
      <label className="form-label" htmlFor="channel-handle">
        YouTube 채널 핸들
      </label>
      <div className="form-row">
        <input
          id="channel-handle"
          name="channel-handle"
          type="text"
          autoComplete="off"
          placeholder="@yourchannel 또는 https://youtube.com/@yourchannel"
          value={inputValue}
          onChange={(event) => setInputValue(event.target.value)}
          className="handle-input"
          aria-invalid={Boolean(error)}
        />
        <button type="submit" className="primary-btn" disabled={!hasValidHandle || isSubmitting}>
          {isSubmitting ? "수집 중..." : "최신 영상 2개 분석"}
        </button>
      </div>
      <p className="form-help">
        입력이 URL이어도 자동으로 핸들 형식으로 변환되며, 최신 영상 2개를 분석합니다.
      </p>
      <p className="form-preview">인식된 핸들: {hasValidHandle ? normalizedHandle : "-"}</p>
      {error ? <p className="form-error">{error}</p> : null}
    </form>
  );
}
