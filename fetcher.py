"""Retrieve YouTube channel analytics or provide educational sample data."""

import logging
import os
import re
from typing import Any, List, Optional

from models import Channel, Video


logger = logging.getLogger(__name__)


class YouTubeDataFetcher:
	"""Fetch channel and video data from YouTube or generate mock data.

	The YouTube Data API is accessed only when an API key is configured. API
	results and fallback samples are both returned as a :class:`Channel` that
	contains :class:`Video` instances, keeping downstream analytics independent
	of the data source.

	Args:
		api_key: Optional YouTube Data API key. When omitted or empty, requests
			to :meth:`fetch_channel_data` use educational mock data.
	"""

	_API_SERVICE = "youtube"
	_API_VERSION = "v3"
	_MOCK_CHANNEL_ID = "@rajshamani"

	def __init__(
		self,
		api_key: Optional[str] = None,
		channel_id: Optional[str] = None,
	) -> None:
		configured_api_key = api_key or os.getenv("YOUTUBE_API_KEY")
		configured_channel_id = channel_id or os.getenv(
			"YOUTUBE_CHANNEL_ID", self._MOCK_CHANNEL_ID
		)
		self._api_key = (
			configured_api_key.strip()
			if configured_api_key and configured_api_key.strip()
			else None
		)
		self._channel_id = configured_channel_id.strip() or self._MOCK_CHANNEL_ID
		self._requested_channel_id: Optional[str] = None
		self._data_source = "not fetched"
		self._fallback_reason: Optional[str] = None

	@property
	def data_source(self) -> str:
		"""Return whether the latest fetch used the live API or mock data."""
		return self._data_source

	@property
	def fallback_reason(self) -> Optional[str]:
		"""Explain why the latest fetch used mock data, if it did."""
		return self._fallback_reason

	def fetch_channel_data(self, channel_id: Optional[str] = None) -> Channel:
		"""Fetch a channel and its latest videos, falling back to sample data.

		The channel's upload playlist is used to find up to 50 recent videos.
		If the API key is absent, the channel cannot be found, or an API request
		fails, a populated educational mock channel is returned instead.

		Args:
			channel_id: Optional YouTube channel ID or @handle. If omitted,
				uses ``YOUTUBE_CHANNEL_ID`` or defaults to ``@rajshamani``.

		Returns:
			A channel populated with video metrics, either live or mock.
		"""
		channel_id = channel_id or self._channel_id
		self._requested_channel_id = channel_id
		self._fallback_reason = None
		if not self._api_key:
			self._fallback_reason = "YOUTUBE_API_KEY is not configured"
			return self.generate_raj_shamani_mock_data()

		try:
			from googleapiclient.discovery import build

			service = build(
				self._API_SERVICE,
				self._API_VERSION,
				developerKey=self._api_key,
			)
			lookup = (
				{"forHandle": channel_id.lstrip("@")} 
				if channel_id.startswith("@")
				else {"id": channel_id}
			)
			channel_response = service.channels().list(
				part="snippet,statistics,contentDetails",
				maxResults=1,
				**lookup,
			).execute()
			channels = channel_response.get("items", [])
			if not channels:
				self._fallback_reason = f"No YouTube channel found for {channel_id}"
				logger.warning("%s; using mock data", self._fallback_reason)
				return self.generate_raj_shamani_mock_data()

			channel_data = channels[0]
			snippet = channel_data.get("snippet", {})
			statistics = channel_data.get("statistics", {})
			content_details = channel_data.get("contentDetails", {})
			uploads_playlist = content_details.get("relatedPlaylists", {}).get("uploads")
			video_ids = self._get_latest_video_ids(service, uploads_playlist)
			videos = self._get_videos(service, video_ids)

			channel = Channel(
				channel_id=channel_data.get("id", channel_id),
				channel_name=snippet.get("title") or "YouTube Channel",
				subscribers=self._parse_count(statistics.get("subscriberCount")),
				total_videos=self._parse_count(statistics.get("videoCount")),
				videos=videos,
			)
			self._data_source = "live"
			return channel
		except Exception as error:
			self._fallback_reason = (
				f"YouTube API request failed ({type(error).__name__})"
			)
			logger.exception("YouTube API request failed; using mock data")
			return self.generate_raj_shamani_mock_data()

	def generate_mock_data(self) -> Channel:
		"""Preserve the generic fallback method as an alias for the show samples."""
		return self.generate_raj_shamani_mock_data()

	def generate_raj_shamani_mock_data(self) -> Channel:
		"""Create sample ``Figuring Out`` videos and illustrative metrics.

		Returns:
			A channel containing multiple mock videos with guest topics and
			categories associated with business, leadership, health, and psychology.
			The view and engagement counts are illustrative, not live statistics.
		"""
		self._data_source = "mock"
		channel = Channel(
			channel_id=self._requested_channel_id or self._channel_id,
			channel_name="Raj Shamani",
			subscribers=5_800_000,
			total_videos=25,
		)
		mock_videos = [
			{
				"video_id": "mock-figuring-out-huberman-habits",
				"title": "Andrew Huberman: Become Mentally Dangerous With These Daily Habits",
				"published_at": "2025-08-12T14:00:00Z",
				"views": 2_840_000,
				"likes": 86_400,
				"comments": 3_280,
				"duration_sec": 5_184,
				"topic": "Psychology & Focus",
			},
			{
				"video_id": "mock-figuring-out-neuroscientist-focus",
				"title": "Neuroscientist Guide To 10X Your Focus & Memory",
				"published_at": "2025-07-24T14:00:00Z",
				"views": 1_960_000,
				"likes": 59_800,
				"comments": 2_140,
				"duration_sec": 4_620,
				"topic": "Health & Brain Science",
			},
			{
				"video_id": "mock-figuring-out-vip-security",
				"title": "Protecting the President: Security & VIP Threats",
				"published_at": "2025-06-30T14:00:00Z",
				"views": 1_420_000,
				"likes": 42_100,
				"comments": 1_760,
				"duration_sec": 4_080,
				"topic": "Leadership",
			},
			{
				"video_id": "mock-figuring-out-brain-science",
				"title": "Top Brain Scientist: Billionaire Brain, Anxiety & Addictions",
				"published_at": "2025-05-18T14:00:00Z",
				"views": 1_780_000,
				"likes": 51_600,
				"comments": 2_480,
				"duration_sec": 5_040,
				"topic": "Health & Brain Science",
			},
			{
				"video_id": "mock-figuring-out-influence",
				"title": "The Psychology Of Seduction & Influence",
				"published_at": "2025-04-09T14:00:00Z",
				"views": 2_210_000,
				"likes": 67_300,
				"comments": 3_140,
				"duration_sec": 4_560,
				"topic": "Psychology & Focus",
			},
			{
				"video_id": "mock-figuring-out-business-growth",
				"title": "Building a Business That Lasts: Growth, Risk & Decision-Making",
				"published_at": "2025-03-16T14:00:00Z",
				"views": 1_640_000,
				"likes": 48_900,
				"comments": 2_020,
				"duration_sec": 4_320,
				"topic": "Business & Growth",
			},
		]
		for video_data in mock_videos:
			channel.add_video(Video(**video_data))

		additional_videos = [
			(
				"mock-dopamine-and-motivation",
				"Andrew Huberman: Dopamine, Motivation and Building Better Habits",
				"2025-03-02T14:00:00Z",
				2_400_000, 143_000, 9_000, 4_920, "Psychology & Focus",
			),
			(
				"mock-rewire-brain-success",
				"How to Rewire Your Brain for Success: A Neuroscientist Explains",
				"2025-02-18T14:00:00Z",
				1_800_000, 105_000, 7_600, 4_680, "Health & Brain Science",
			),
			(
				"mock-billionaire-founder-mindset",
				"Inside a Billionaire Founder's Mind: Risk, Failure and Growth",
				"2025-02-04T14:00:00Z",
				2_100_000, 102_000, 8_000, 5_100, "Business & Growth",
			),
			(
				"mock-protect-world-leaders",
				"How Security Teams Protect World Leaders from Real Threats",
				"2025-01-21T14:00:00Z",
				1_200_000, 68_000, 5_000, 4_260, "Leadership",
			),
			(
				"mock-stop-procrastinating",
				"Why We Procrastinate and How to Take Back Your Focus",
				"2025-01-08T14:00:00Z",
				950_000, 57_000, 4_400, 3_900, "Psychology & Focus",
			),
			(
				"mock-sleep-and-performance",
				"The Science of Sleep: Brain Health, Memory and Performance",
				"2024-12-24T14:00:00Z",
				1_500_000, 78_000, 6_000, 4_500, "Health & Brain Science",
			),
			(
				"mock-building-wealth",
				"Building Wealth from Zero: Investing, Patience and Discipline",
				"2024-12-10T14:00:00Z",
				1_100_000, 66_000, 4_500, 4_380, "Business & Growth",
			),
			(
				"mock-leadership-pressure",
				"How Great Leaders Make Decisions Under Pressure",
				"2024-11-26T14:00:00Z",
				830_000, 47_000, 3_300, 3_960, "Leadership",
			),
			(
				"mock-focus-distracted-world",
				"Focus in a Distracted World: Practical Tools for Deep Work",
				"2024-11-12T14:00:00Z",
				1_300_000, 68_000, 5_100, 4_140, "Psychology & Focus",
			),
			(
				"mock-nutrition-mental-clarity",
				"Nutrition, Gut Health and Mental Clarity Explained",
				"2024-10-29T14:00:00Z",
				1_700_000, 70_000, 4_100, 4_800, "Health & Brain Science",
			),
			(
				"mock-startup-growth",
				"From First Customer to Global Company: Lessons in Startup Growth",
				"2024-10-15T14:00:00Z",
				2_700_000, 92_000, 5_200, 5_280, "Business & Growth",
			),
			(
				"mock-persuasive-communication",
				"The Psychology of Persuasive Communication and Influence",
				"2024-10-01T14:00:00Z",
				800_000, 40_000, 2_600, 3_780, "Leadership",
			),
			(
				"mock-understanding-anxiety",
				"Understanding Anxiety: What Happens in the Brain and Body",
				"2024-09-17T14:00:00Z",
				1_200_000, 60_000, 4_800, 4_560, "Health & Brain Science",
			),
			(
				"mock-effective-habits",
				"The Habits of Highly Effective People: A Practical Conversation",
				"2024-09-03T14:00:00Z",
				3_100_000, 105_000, 6_000, 4_920, "Psychology & Focus",
			),
			(
				"mock-scaling-company-culture",
				"Scaling a Company Without Losing Its Culture",
				"2024-08-20T14:00:00Z",
				650_000, 27_000, 1_700, 4_080, "Business & Growth",
			),
			(
				"mock-confidence-charisma",
				"The Psychology of Confidence, Charisma and Self-Belief",
				"2024-08-06T14:00:00Z",
				1_400_000, 79_000, 5_600, 4_320, "Psychology & Focus",
			),
			(
				"mock-high-stakes-negotiation",
				"Inside High-Stakes Negotiations: Preparation, Patience and Trust",
				"2024-07-23T14:00:00Z",
				980_000, 49_000, 3_800, 4_500, "Leadership",
			),
			(
				"mock-ai-and-future-of-work",
				"The Future of AI and Work: Skills, Business and Opportunity",
				"2024-07-09T14:00:00Z",
				2_200_000, 70_000, 5_000, 4_740, "Business & Growth",
			),
			(
				"mock-understanding-addiction",
				"A Practical Guide to Understanding Addiction and Recovery",
				"2024-06-25T14:00:00Z",
				1_600_000, 86_000, 7_200, 4_860, "Health & Brain Science",
			),
		]
		for video_data in additional_videos:
			video_id, title, published_at, views, likes, comments, duration_sec, topic = video_data
			channel.add_video(
				Video(
					video_id=video_id,
					title=title,
					published_at=published_at,
					views=views,
					likes=likes,
					comments=comments,
					duration_sec=duration_sec,
					topic=topic,
				)
			)
		return channel

	@staticmethod
	def _get_latest_video_ids(service: Any, uploads_playlist: Optional[str]) -> List[str]:
		"""Return video IDs from up to 50 recent entries in an uploads playlist."""
		if not uploads_playlist:
			return []
		response = service.playlistItems().list(
			part="contentDetails",
			playlistId=uploads_playlist,
			maxResults=50,
		).execute()
		return [
			item.get("contentDetails", {}).get("videoId")
			for item in response.get("items", [])
			if item.get("contentDetails", {}).get("videoId")
		]

	@classmethod
	def _get_videos(cls, service: Any, video_ids: List[str]) -> List[Video]:
		"""Fetch video metrics and metadata for the supplied video IDs."""
		videos: List[Video] = []
		for start in range(0, len(video_ids), 50):
			batch_ids = video_ids[start:start + 50]
			response = service.videos().list(
				part="snippet,statistics,contentDetails",
				id=",".join(batch_ids),
				maxResults=50,
			).execute()
			for item in response.get("items", []):
				snippet = item.get("snippet", {})
				statistics = item.get("statistics", {})
				videos.append(
					Video(
						video_id=item.get("id", "unknown-video"),
						title=snippet.get("title") or "Untitled video",
						published_at=snippet.get("publishedAt") or "",
						views=cls._parse_count(statistics.get("viewCount")),
						likes=cls._parse_count(statistics.get("likeCount")),
						comments=cls._parse_count(statistics.get("commentCount")),
						duration_sec=cls._duration_to_seconds(
							item.get("contentDetails", {}).get("duration", "")
						),
						topic=cls._infer_topic(
							snippet.get("title", ""), snippet.get("description", "")
						),
					)
				)
		return videos

	@staticmethod
	def _parse_count(value: Any) -> int:
		"""Convert an API count to a non-negative integer, defaulting to zero."""
		try:
			return max(0, int(value or 0))
		except (TypeError, ValueError):
			return 0

	@staticmethod
	def _duration_to_seconds(duration: str) -> int:
		"""Convert an ISO 8601 YouTube duration such as ``PT12M30S`` to seconds."""
		match = re.fullmatch(
			r"P(?:(\d+)D)?(?:T(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?)?",
			duration,
		)
		if not match:
			return 0
		days, hours, minutes, seconds = (int(part or 0) for part in match.groups())
		return days * 86_400 + hours * 3_600 + minutes * 60 + seconds

	@staticmethod
	def _infer_topic(title: str, description: str) -> str:
		"""Infer a broad learning level from video metadata keywords."""
		text = f"{title} {description}".lower()
		if any(word in text for word in ("advanced", "architecture", "system design", "deep dive")):
			return "Advanced"
		if any(word in text for word in ("beginner", "basics", "introduction", "intro to")):
			return "Beginner"
		if any(word in text for word in ("intermediate", "data structures", "tutorial")):
			return "Intermediate"
		return "Educational"
