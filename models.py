"""Domain models for the YouTube educational content analytics system.

``Channel`` aggregates ``Video`` objects, while each ``Video`` owns the
engagement calculation and its own metadata. The classes keep state in private
attributes and expose validated properties for controlled access.
"""

from datetime import datetime
from typing import Dict, List, Optional, Union


PublishedAt = Union[str, datetime]


def _validate_non_negative_int(value: int, field_name: str) -> int:
	"""Return an integer metric after rejecting invalid or negative values."""
	if isinstance(value, bool) or not isinstance(value, int):
		raise TypeError(f"{field_name} must be an integer")
	if value < 0:
		raise ValueError(f"{field_name} cannot be negative")
	return value


class Video:
	"""Represent one educational YouTube video and its performance metrics.

	Attributes are exposed through properties, while the corresponding state
	is stored privately. Engagement rate is measured as the percentage of
	views that resulted in a like or comment:

	``(likes + comments) / views * 100``.

	Args:
		video_id: YouTube's unique identifier for the video.
		title: Human-readable video title.
		published_at: Publication timestamp, either ISO-formatted text or a
			:class:`datetime.datetime` instance.
		views: Number of views recorded for the video.
		likes: Number of likes recorded for the video.
		comments: Number of comments recorded for the video.
		duration_sec: Video duration in seconds.
		topic: Educational subject or category assigned to the video.
	"""

	__slots__ = (
		"_video_id",
		"_title",
		"_published_at",
		"_views",
		"_likes",
		"_comments",
		"_duration_sec",
		"_topic",
	)

	def __init__(
		self,
		video_id: str,
		title: str,
		published_at: PublishedAt,
		views: int,
		likes: int,
		comments: int,
		duration_sec: int,
		topic: str,
	) -> None:
		self.video_id = video_id
		self.title = title
		self.published_at = published_at
		self.views = views
		self.likes = likes
		self.comments = comments
		self.duration_sec = duration_sec
		self.topic = topic

	@property
	def video_id(self) -> str:
		"""Return the video's unique YouTube identifier."""
		return self._video_id

	@video_id.setter
	def video_id(self, value: str) -> None:
		if not isinstance(value, str) or not value.strip():
			raise ValueError("video_id must be a non-empty string")
		self._video_id = value

	@property
	def title(self) -> str:
		"""Return the video title."""
		return self._title

	@title.setter
	def title(self, value: str) -> None:
		if not isinstance(value, str) or not value.strip():
			raise ValueError("title must be a non-empty string")
		self._title = value

	@property
	def published_at(self) -> PublishedAt:
		"""Return the publication date as text or a datetime value."""
		return self._published_at

	@published_at.setter
	def published_at(self, value: PublishedAt) -> None:
		if not isinstance(value, (str, datetime)):
			raise TypeError("published_at must be a string or datetime")
		self._published_at = value

	@property
	def views(self) -> int:
		"""Return the number of views."""
		return self._views

	@views.setter
	def views(self, value: int) -> None:
		self._views = _validate_non_negative_int(value, "views")

	@property
	def likes(self) -> int:
		"""Return the number of likes."""
		return self._likes

	@likes.setter
	def likes(self, value: int) -> None:
		self._likes = _validate_non_negative_int(value, "likes")

	@property
	def comments(self) -> int:
		"""Return the number of comments."""
		return self._comments

	@comments.setter
	def comments(self, value: int) -> None:
		self._comments = _validate_non_negative_int(value, "comments")

	@property
	def duration_sec(self) -> int:
		"""Return the video duration in seconds."""
		return self._duration_sec

	@duration_sec.setter
	def duration_sec(self, value: int) -> None:
		self._duration_sec = _validate_non_negative_int(value, "duration_sec")

	@property
	def topic(self) -> str:
		"""Return the video's educational topic."""
		return self._topic

	@topic.setter
	def topic(self, value: str) -> None:
		if not isinstance(value, str) or not value.strip():
			raise ValueError("topic must be a non-empty string")
		self._topic = value

	def calculate_engagement_rate(self) -> float:
		"""Return likes plus comments as a percentage of views.

		A video with no views has no measurable engagement rate, so this
		method returns ``0.0`` instead of dividing by zero.
		"""
		if self.views == 0:
			return 0.0
		return (self.likes + self.comments) / self.views * 100.0

	def to_dict(self) -> Dict[str, object]:
		"""Return the video's stored attributes as a plain dictionary.

		A ``datetime`` publication value is converted to ISO 8601 text so the
		result is convenient to serialize or write to tabular output.
		"""
		published_at = self.published_at
		if isinstance(published_at, datetime):
			published_at = published_at.isoformat()
		return {
			"video_id": self.video_id,
			"title": self.title,
			"published_at": published_at,
			"views": self.views,
			"likes": self.likes,
			"comments": self.comments,
			"duration_sec": self.duration_sec,
			"topic": self.topic,
		}


class Channel:
	"""Represent a YouTube channel and the videos associated with it.

	A channel contains a collection of :class:`Video` objects. It can add
	videos and derive aggregate performance measures from their engagement
	rates.

	Args:
		channel_id: YouTube's unique identifier for the channel.
		channel_name: Human-readable channel name.
		subscribers: Number of subscribers recorded for the channel.
		total_videos: Number of videos reported for the channel.
		videos: Optional initial collection of :class:`Video` objects.
	"""

	__slots__ = (
		"_channel_id",
		"_channel_name",
		"_subscribers",
		"_total_videos",
		"_videos",
	)

	def __init__(
		self,
		channel_id: str,
		channel_name: str,
		subscribers: int,
		total_videos: int,
		videos: Optional[List[Video]] = None,
	) -> None:
		self.channel_id = channel_id
		self.channel_name = channel_name
		self.subscribers = subscribers
		self.total_videos = total_videos
		self._videos: List[Video] = []
		for video in videos or []:
			self.add_video(video)

	@property
	def channel_id(self) -> str:
		"""Return the channel's unique YouTube identifier."""
		return self._channel_id

	@channel_id.setter
	def channel_id(self, value: str) -> None:
		if not isinstance(value, str) or not value.strip():
			raise ValueError("channel_id must be a non-empty string")
		self._channel_id = value

	@property
	def channel_name(self) -> str:
		"""Return the channel's display name."""
		return self._channel_name

	@channel_name.setter
	def channel_name(self, value: str) -> None:
		if not isinstance(value, str) or not value.strip():
			raise ValueError("channel_name must be a non-empty string")
		self._channel_name = value

	@property
	def subscribers(self) -> int:
		"""Return the channel's subscriber count."""
		return self._subscribers

	@subscribers.setter
	def subscribers(self, value: int) -> None:
		self._subscribers = _validate_non_negative_int(value, "subscribers")

	@property
	def total_videos(self) -> int:
		"""Return the total video count reported for the channel."""
		return self._total_videos

	@total_videos.setter
	def total_videos(self, value: int) -> None:
		self._total_videos = _validate_non_negative_int(value, "total_videos")

	@property
	def videos(self) -> List[Video]:
		"""Return a copy of the channel's video collection.

		Returning a copy prevents callers from bypassing :meth:`add_video`
		and inserting values that are not ``Video`` instances.
		"""
		return self._videos.copy()

	def add_video(self, video: Video) -> None:
		"""Add a ``Video`` to this channel's collection.

		Args:
			video: The video object to associate with this channel.

		Raises:
			TypeError: If ``video`` is not a :class:`Video` instance.
		"""
		if not isinstance(video, Video):
			raise TypeError("video must be a Video instance")
		self._videos.append(video)

	def get_average_engagement(self) -> float:
		"""Return the mean engagement rate across the channel's videos.

		Returns ``0.0`` when the channel does not yet contain any videos.
		"""
		if not self._videos:
			return 0.0
		return sum(
			video.calculate_engagement_rate() for video in self._videos
		) / len(self._videos)

	def get_top_performing_video(self) -> Optional[Video]:
		"""Return the video with the highest engagement rate, if any.

		Ties are resolved in favor of the video added first. Returns ``None``
		when the channel has no videos.
		"""
		if not self._videos:
			return None
		return max(self._videos, key=lambda video: video.calculate_engagement_rate())
