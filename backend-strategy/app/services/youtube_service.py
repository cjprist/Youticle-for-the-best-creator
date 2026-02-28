"""YouTube Data API client for collecting latest video comments."""

from __future__ import annotations

from typing import Literal
from typing import Any

import httpx

from app.config import get_settings


class YouTubeDataAPIError(RuntimeError):
    """Raised when YouTube Data API returns an error response."""


class YouTubeCommentService:
    def __init__(self, *, timeout: float = 15.0) -> None:
        settings = get_settings()
        if not settings.youtube_data_api_key:
            raise ValueError("YOUTUBE_DATA_API_KEY is required to call YouTube Data API.")

        self.api_key = settings.youtube_data_api_key
        self.base_url = settings.youtube_api_base_url.rstrip("/")
        self.timeout = timeout

    def fetch_channel_comments(
        self,
        channel_handle: str,
        max_videos: int = 10,
        max_comments_per_video: int = 10,
        comment_order: Literal["top", "latest"] = "top",
    ) -> dict[str, Any]:
        handle = channel_handle.strip()
        if not handle:
            raise ValueError("Channel handle must not be empty.")
        if not handle.startswith("@"):
            handle = f"@{handle}"

        channel_info = self._resolve_channel_info(handle)
        channel_id = channel_info["channel_id"]
        videos = self._fetch_latest_videos(channel_id, max_videos)

        video_payloads: list[dict[str, Any]] = []
        for video in videos:
            comments = self._fetch_comments_for_video(
                video["id"],
                max_comments_per_video=max_comments_per_video,
                comment_order=comment_order,
            )
            video_payloads.append(
                {
                    "video_id": video["id"],
                    "video_title": video["title"],
                    "thumbnail_url": video["thumbnail_url"],
                    "published_at": video["published_at"],
                    "comment_count": len(comments),
                    "comments": comments,
                }
            )

        return {
            "channel_handle": handle,
            "channel_id": channel_id,
            "channel_name": channel_info.get("channel_name"),
            "channel_thumbnail_url": channel_info.get("channel_thumbnail_url"),
            "subscriber_count": channel_info.get("subscriber_count"),
            "video_count": len(video_payloads),
            "videos": video_payloads,
        }

    def _resolve_channel_info(self, handle: str) -> dict[str, Any]:
        data = self._get(
            "channels",
            {
                "part": "id,snippet,statistics",
                "forHandle": handle,
            },
        )
        items = data.get("items", [])
        if not items:
            raise YouTubeDataAPIError(f"Could not resolve channel id for handle '{handle}'.")
        channel = items[0]
        snippet = channel.get("snippet", {})
        statistics = channel.get("statistics", {})
        thumbnails = snippet.get("thumbnails", {})
        thumb = (
            thumbnails.get("high", {}).get("url")
            or thumbnails.get("medium", {}).get("url")
            or thumbnails.get("default", {}).get("url")
        )
        subscriber_count = statistics.get("subscriberCount")
        return {
            "channel_id": channel.get("id", ""),
            "channel_name": snippet.get("title"),
            "channel_thumbnail_url": thumb,
            "subscriber_count": int(subscriber_count) if str(subscriber_count).isdigit() else None,
        }

    def _fetch_latest_videos(self, channel_id: str, max_videos: int) -> list[dict[str, Any]]:
        params = {
            "part": "snippet",
            "channelId": channel_id,
            "order": "date",
            "type": "video",
            "maxResults": min(max_videos, 50),
        }
        data = self._get("search", params)
        videos: list[dict[str, Any]] = []
        for item in data.get("items", []):
            video_id = item.get("id", {}).get("videoId")
            snippet = item.get("snippet", {})
            if not video_id:
                continue
            videos.append(
                {
                    "id": video_id,
                    "title": snippet.get("title", ""),
                    "thumbnail_url": (
                        snippet.get("thumbnails", {}).get("high", {}).get("url")
                        or snippet.get("thumbnails", {}).get("medium", {}).get("url")
                        or snippet.get("thumbnails", {}).get("default", {}).get("url")
                    ),
                    "published_at": snippet.get("publishedAt"),
                }
            )
            if len(videos) >= max_videos:
                break
        return videos

    def _fetch_comments_for_video(
        self,
        video_id: str,
        *,
        max_comments_per_video: int = 10,
        comment_order: Literal["top", "latest"] = "top",
    ) -> list[dict[str, Any]]:
        youtube_order = "relevance" if comment_order == "top" else "time"
        params = {
            "part": "snippet",
            "videoId": video_id,
            "textFormat": "plainText",
            "maxResults": min(max_comments_per_video, 100),
            "order": youtube_order,
        }
        comments: list[dict[str, Any]] = []
        data = self._get("commentThreads", params)
        for item in data.get("items", []):
            top_level = item.get("snippet", {}).get("topLevelComment", {})
            comment_payload = self._build_comment_payload(top_level, parent_id=None)
            if comment_payload:
                comments.append(comment_payload)
            if len(comments) >= max_comments_per_video:
                break

        # Keep top mode deterministic by explicitly prioritizing higher like_count.
        if comment_order == "top":
            comments.sort(key=lambda c: int(c.get("like_count", 0)), reverse=True)
        return comments[:max_comments_per_video]

    def _build_comment_payload(
        self, comment: dict[str, Any] | None, *, parent_id: str | None
    ) -> dict[str, Any] | None:
        if not comment:
            return None
        snippet = comment.get("snippet", {})
        return {
            "comment_id": comment.get("id", ""),
            "parent_comment_id": parent_id,
            "author": snippet.get("authorDisplayName"),
            "text": snippet.get("textDisplay", ""),
            "like_count": snippet.get("likeCount", 0),
            "published_at": snippet.get("publishedAt"),
        }

    def _get(self, endpoint: str, params: dict[str, Any]) -> dict[str, Any]:
        url = f"{self.base_url}/{endpoint}"
        query = {**params, "key": self.api_key}
        response = httpx.get(url, params=query, timeout=self.timeout)
        if response.status_code != httpx.codes.OK:
            try:
                payload = response.json()
                message = payload.get("error", {}).get("message", response.text)
            except ValueError:
                message = response.text
            raise YouTubeDataAPIError(f"YouTube API error ({response.status_code}): {message}")
        try:
            return response.json()
        except ValueError as exc:
            raise YouTubeDataAPIError("Invalid JSON returned from YouTube API.") from exc
