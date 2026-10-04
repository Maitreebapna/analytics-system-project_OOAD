"""SQLite persistence for current data and historical analytics snapshots."""

import sqlite3
from datetime import datetime, timezone
from typing import Dict, Iterable, Optional

from models import Channel


class YouTubeDatabase:
	"""Store current channel data and dated analytics snapshots in SQLite."""

	def __init__(self, database_path: str = "youtube_analytics.db") -> None:
		self.database_path = database_path
		self._initialize()

	def _initialize(self) -> None:
		connection = sqlite3.connect(self.database_path)
		try:
			connection.execute("PRAGMA foreign_keys = ON")
			connection.executescript(
				"""
				CREATE TABLE IF NOT EXISTS channels (
					channel_id TEXT PRIMARY KEY,
					channel_name TEXT NOT NULL,
					subscribers INTEGER NOT NULL,
					total_videos INTEGER NOT NULL
				);

				CREATE TABLE IF NOT EXISTS videos (
					video_id TEXT PRIMARY KEY,
					channel_id TEXT NOT NULL,
					title TEXT NOT NULL,
					published_at TEXT NOT NULL,
					views INTEGER NOT NULL,
					likes INTEGER NOT NULL,
					comments INTEGER NOT NULL,
					duration_sec INTEGER NOT NULL,
					topic TEXT NOT NULL,
					FOREIGN KEY (channel_id) REFERENCES channels(channel_id)
				);

				CREATE TABLE IF NOT EXISTS analytics_snapshots (
					snapshot_id INTEGER PRIMARY KEY AUTOINCREMENT,
					captured_at TEXT NOT NULL,
					data_source TEXT NOT NULL CHECK (data_source IN ('live', 'mock')),
					channel_id TEXT NOT NULL,
					channel_name TEXT NOT NULL,
					subscribers INTEGER NOT NULL,
					total_videos INTEGER NOT NULL,
					videos_analyzed INTEGER NOT NULL,
					FOREIGN KEY (channel_id) REFERENCES channels(channel_id)
				);

				CREATE TABLE IF NOT EXISTS video_analytics_snapshots (
					snapshot_id INTEGER NOT NULL,
					video_id TEXT NOT NULL,
					title TEXT NOT NULL,
					published_at TEXT NOT NULL,
					views INTEGER NOT NULL,
					likes INTEGER NOT NULL,
					comments INTEGER NOT NULL,
					duration_sec INTEGER NOT NULL,
					topic TEXT NOT NULL,
					engagement_rate REAL NOT NULL,
					like_to_view_ratio REAL NOT NULL,
					performance_category TEXT NOT NULL,
					PRIMARY KEY (snapshot_id, video_id),
					FOREIGN KEY (snapshot_id)
						REFERENCES analytics_snapshots(snapshot_id) ON DELETE CASCADE
				);

				CREATE INDEX IF NOT EXISTS idx_analytics_snapshots_channel_time
					ON analytics_snapshots(channel_id, captured_at);

				CREATE VIEW IF NOT EXISTS powerbi_video_analytics AS
				SELECT
					s.snapshot_id,
					s.captured_at,
					s.data_source,
					s.channel_id AS Channel_ID,
					s.channel_name AS Channel_Name,
					s.subscribers AS Subscribers,
					s.total_videos AS Total_Videos,
					v.video_id,
					v.title,
					v.published_at,
					v.views,
					v.likes,
					v.comments,
					v.duration_sec,
					v.topic,
					v.engagement_rate AS Engagement_Rate,
					v.like_to_view_ratio AS Like_To_View_Ratio,
					v.performance_category AS Performance_Category
				FROM analytics_snapshots AS s
				JOIN video_analytics_snapshots AS v
					ON v.snapshot_id = s.snapshot_id;
				"""
			)
			connection.commit()
		finally:
			connection.close()

	def save_channel(self, channel: Channel) -> None:
		"""Insert or update the latest channel and video records."""
		self._validate_channel(channel)
		connection = sqlite3.connect(self.database_path)
		try:
			connection.execute("PRAGMA foreign_keys = ON")
			with connection:
				self._upsert_channel(connection, channel)
		finally:
			connection.close()

	def save_snapshot(
		self,
		channel: Channel,
		metrics: Iterable[Dict[str, object]],
		data_source: str,
	) -> int:
		"""Atomically save current records and a dated set of calculated metrics."""
		self._validate_channel(channel)
		if data_source not in {"live", "mock"}:
			raise ValueError("data_source must be 'live' or 'mock'")

		metric_rows = list(metrics)
		if len(metric_rows) != len(channel.videos):
			raise ValueError("metrics must contain one row for each channel video")

		connection = sqlite3.connect(self.database_path)
		try:
			connection.execute("PRAGMA foreign_keys = ON")
			with connection:
				self._upsert_channel(connection, channel)
				captured_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
				cursor = connection.execute(
					"""
					INSERT INTO analytics_snapshots (
						captured_at, data_source, channel_id, channel_name,
						subscribers, total_videos, videos_analyzed
					) VALUES (?, ?, ?, ?, ?, ?, ?)
					""",
					(
						captured_at,
						data_source,
						channel.channel_id,
						channel.channel_name,
						channel.subscribers,
						channel.total_videos,
						len(metric_rows),
					),
				)
				snapshot_id = cursor.lastrowid
				connection.executemany(
					"""
					INSERT INTO video_analytics_snapshots (
						snapshot_id, video_id, title, published_at, views, likes,
						comments, duration_sec, topic, engagement_rate,
						like_to_view_ratio, performance_category
					) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
					""",
					[
						(
							snapshot_id,
							row["video_id"],
							row["title"],
							row["published_at"],
							row["views"],
							row["likes"],
							row["comments"],
							row["duration_sec"],
							row["topic"],
							row["Engagement_Rate"],
							row["Like_To_View_Ratio"],
							row["Performance_Category"],
						)
						for row in metric_rows
					],
				)
			return int(snapshot_id)
		finally:
			connection.close()

	def get_latest_snapshot(
		self,
		channel_id: Optional[str] = None,
	) -> Optional[Dict[str, object]]:
		"""Return the newest saved snapshot and its video metrics, if available."""
		connection = sqlite3.connect(self.database_path)
		connection.row_factory = sqlite3.Row
		try:
			query = """
				SELECT snapshot_id, captured_at, data_source, channel_id,
					channel_name, subscribers, total_videos, videos_analyzed
				FROM analytics_snapshots
			"""
			parameters = ()
			if channel_id is not None:
				query += " WHERE channel_id = ?"
				parameters = (channel_id,)
			query += " ORDER BY snapshot_id DESC LIMIT 1"
			snapshot_row = connection.execute(query, parameters).fetchone()
			if snapshot_row is None:
				return None

			snapshot = dict(snapshot_row)
			snapshot["videos"] = [
				dict(row)
				for row in connection.execute(
					"""
					SELECT video_id, title, published_at, views, likes, comments,
						duration_sec, topic, engagement_rate, like_to_view_ratio,
						performance_category
					FROM video_analytics_snapshots
					WHERE snapshot_id = ?
					ORDER BY engagement_rate DESC, views DESC
					""",
					(snapshot["snapshot_id"],),
				).fetchall()
			]
			return snapshot
		finally:
			connection.close()

	@staticmethod
	def _validate_channel(channel: Channel) -> None:
		if not isinstance(channel, Channel):
			raise TypeError("channel must be a Channel instance")

	@staticmethod
	def _upsert_channel(connection: sqlite3.Connection, channel: Channel) -> None:
		connection.execute(
			"""
			INSERT INTO channels (
				channel_id, channel_name, subscribers, total_videos
			) VALUES (?, ?, ?, ?)
			ON CONFLICT(channel_id) DO UPDATE SET
				channel_name = excluded.channel_name,
				subscribers = excluded.subscribers,
				total_videos = excluded.total_videos
			""",
			(
				channel.channel_id,
				channel.channel_name,
				channel.subscribers,
				channel.total_videos,
			),
		)
		for video in channel.videos:
			video_data = video.to_dict()
			connection.execute(
				"""
				INSERT INTO videos (
					video_id, channel_id, title, published_at, views, likes,
					comments, duration_sec, topic
				) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
				ON CONFLICT(video_id) DO UPDATE SET
					channel_id = excluded.channel_id,
					title = excluded.title,
					published_at = excluded.published_at,
					views = excluded.views,
					likes = excluded.likes,
					comments = excluded.comments,
					duration_sec = excluded.duration_sec,
					topic = excluded.topic
				""",
				(
					video_data["video_id"],
					channel.channel_id,
					video_data["title"],
					video_data["published_at"],
					video_data["views"],
					video_data["likes"],
					video_data["comments"],
					video_data["duration_sec"],
					video_data["topic"],
				),
			)