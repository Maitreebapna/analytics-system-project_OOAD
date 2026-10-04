"""SQLite persistence for YouTube channel and video data."""

import sqlite3

from models import Channel


class YouTubeDatabase:
	"""Store fetched YouTube channel and video data in a SQLite database."""

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
				"""
			)
			connection.commit()
		finally:
			connection.close()

	def save_channel(self, channel: Channel) -> None:
		"""Insert or update a channel and its videos."""
		if not isinstance(channel, Channel):
			raise TypeError("channel must be a Channel instance")

		connection = sqlite3.connect(self.database_path)
		try:
			connection.execute("PRAGMA foreign_keys = ON")
			with connection:
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
		finally:
			connection.close()