"""HTTP API for a browser-based YouTube analytics frontend."""

import os
from contextlib import asynccontextmanager
from functools import lru_cache
from typing import Dict, List, Literal, Optional

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from data_service import DATABASE_PATH, refresh_data
from database import YouTubeDatabase


DEFAULT_FRONTEND_ORIGINS = [
	"http://localhost:3000",
	"http://127.0.0.1:3000",
	"http://localhost:5173",
	"http://127.0.0.1:5173",
	"http://localhost:5500",
	"http://127.0.0.1:5500",
]


@lru_cache(maxsize=1)
def get_database() -> YouTubeDatabase:
	return YouTubeDatabase(str(DATABASE_PATH))


@asynccontextmanager
async def lifespan(_: FastAPI):
	get_database()
	yield


app = FastAPI(
	title="YouTube Analytics API",
	description="Read analytics snapshots and refresh YouTube channel data.",
	version="1.0.0",
	lifespan=lifespan,
)

configured_origins = os.getenv("FRONTEND_ORIGINS")
allowed_origins = (
	[origin.strip() for origin in configured_origins.split(",") if origin.strip()]
	if configured_origins
	else DEFAULT_FRONTEND_ORIGINS
)
app.add_middleware(
	CORSMiddleware,
	allow_origins=allowed_origins,
	allow_credentials=False,
	allow_methods=["GET", "POST"],
	allow_headers=["Content-Type"],
)


class RefreshRequest(BaseModel):
	channel_id: Optional[str] = None


def _latest_snapshot(channel_id: Optional[str] = None) -> Dict[str, object]:
	snapshot = get_database().get_latest_snapshot(channel_id)
	if snapshot is None:
		raise HTTPException(
			status_code=503,
			detail="No analytics snapshot exists yet. Run POST /api/refresh first.",
		)
	return snapshot


@app.get("/api/health")
def health() -> Dict[str, object]:
	snapshot = get_database().get_latest_snapshot()
	return {
		"status": "ok",
		"has_snapshot": snapshot is not None,
		"latest_snapshot_id": snapshot["snapshot_id"] if snapshot else None,
	}


@app.get("/api/dashboard")
def dashboard(channel_id: Optional[str] = None) -> Dict[str, object]:
	snapshot = _latest_snapshot(channel_id)
	videos = snapshot["videos"]
	assert isinstance(videos, list)
	return {
		"snapshot_id": snapshot["snapshot_id"],
		"captured_at": snapshot["captured_at"],
		"data_source": snapshot["data_source"],
		"channel": {
			"channel_id": snapshot["channel_id"],
			"channel_name": snapshot["channel_name"],
			"subscribers": snapshot["subscribers"],
			"total_videos": snapshot["total_videos"],
		},
		"metrics": {
			"videos_analyzed": len(videos),
			"total_views": sum(video["views"] for video in videos),
			"average_engagement_rate": (
				sum(video["engagement_rate"] for video in videos) / len(videos)
				if videos
				else 0.0
			),
		},
	}


@app.get("/api/videos")
def videos(
	channel_id: Optional[str] = None,
	topic: Optional[str] = None,
	performance_category: Optional[str] = None,
	search: Optional[str] = None,
	sort_by: Literal["views", "engagement_rate", "published_at"] = "views",
	sort_order: Literal["asc", "desc"] = "desc",
	limit: int = Query(default=50, ge=1, le=200),
	offset: int = Query(default=0, ge=0),
) -> Dict[str, object]:
	snapshot = _latest_snapshot(channel_id)
	items = list(snapshot["videos"])
	if topic:
		items = [video for video in items if video["topic"].casefold() == topic.casefold()]
	if performance_category:
		items = [
			video
			for video in items
			if video["performance_category"].casefold()
			== performance_category.casefold()
		]
	if search:
		search_term = search.casefold()
		items = [
			video
			for video in items
			if search_term in video["title"].casefold()
			or search_term in video["topic"].casefold()
		]
	items.sort(key=lambda video: video[sort_by], reverse=sort_order == "desc")
	total = len(items)
	return {
		"snapshot_id": snapshot["snapshot_id"],
		"total": total,
		"limit": limit,
		"offset": offset,
		"items": items[offset:offset + limit],
	}


@app.get("/api/recommendations")
def recommendations(
	topic: str = Query(min_length=1),
	max_duration_mins: float = Query(default=120, ge=0, le=1440),
	channel_id: Optional[str] = None,
) -> Dict[str, object]:
	requested_topic = topic.strip().casefold()
	if not requested_topic:
		raise HTTPException(status_code=422, detail="topic cannot be blank")

	snapshot = _latest_snapshot(channel_id)
	matching_videos = [
		video
		for video in snapshot["videos"]
		if video["topic"].casefold() == requested_topic
		and video["duration_sec"] <= max_duration_mins * 60
	]
	matching_videos.sort(
		key=lambda video: (video["engagement_rate"], video["views"]),
		reverse=True,
	)
	return {
		"snapshot_id": snapshot["snapshot_id"],
		"topic": topic.strip(),
		"items": [
			{
				"step": index,
				"video_id": video["video_id"],
				"title": video["title"],
				"topic": video["topic"],
				"duration_mins": video["duration_sec"] / 60,
				"views": video["views"],
				"engagement_rate": video["engagement_rate"],
				"performance_category": video["performance_category"],
			}
			for index, video in enumerate(matching_videos, start=1)
		],
	}


@app.post("/api/refresh")
def refresh(request: Optional[RefreshRequest] = None) -> Dict[str, object]:
	result = refresh_data(request.channel_id if request else None)
	return {
		"snapshot_id": result.snapshot_id,
		"data_source": result.data_source,
		"fallback_reason": result.fallback_reason,
		"channel_id": result.channel.channel_id,
		"channel_name": result.channel.channel_name,
		"videos_analyzed": len(result.channel.videos),
	}