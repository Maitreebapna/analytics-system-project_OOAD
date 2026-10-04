"""Analytics and learning recommendations for YouTube channel videos."""

import math
from typing import Dict, List, Union

import pandas as pd

from models import Channel


class AnalyticsEngine:
	"""Analyze a channel's video performance and recommend learning content.

	The engine works with a :class:`models.Channel` and its associated
	:class:`models.Video` objects. Engagement rates are percentages, while
	``Like_To_View_Ratio`` is a decimal ratio between zero and one for ordinary
	YouTube data.

	Args:
		channel: Channel whose video data will be analyzed.
	"""

	VIRAL_ENGAGEMENT_THRESHOLD = 5.0
	VIRAL_VIEW_THRESHOLD = 10_000_000
	HIGH_ENGAGEMENT_THRESHOLD = 2.5

	_DATAFRAME_COLUMNS = [
		"video_id",
		"title",
		"published_at",
		"views",
		"likes",
		"comments",
		"duration_sec",
		"topic",
		"Engagement_Rate",
		"Like_To_View_Ratio",
		"Performance_Category",
		"Channel_ID",
		"Channel_Name",
		"Subscribers",
	]

	def __init__(self, channel: Channel) -> None:
		if not isinstance(channel, Channel):
			raise TypeError("channel must be a Channel instance")
		self.channel = channel

	def compute_metrics_dataframe(self) -> pd.DataFrame:
		"""Build a video-level dataframe with derived performance statistics.

		Each row contains the video's original model data, engagement rate,
		like-to-view ratio, performance category, and channel identifiers useful
		for grouping the data in Power BI. A video is ``Viral Hit`` when its
		engagement rate exceeds 5% or its views exceed 10 million. Otherwise,
		2.5% through 5% is ``High Engagement`` and below 2.5% is ``Steady Growth``.

		Returns:
			A pandas DataFrame, including a stable set of columns when there are
			no videos in the channel.
		"""
		rows = [video.to_dict() for video in self.channel.videos]
		dataframe = pd.DataFrame(rows)
		if dataframe.empty:
			dataframe = pd.DataFrame(columns=self._DATAFRAME_COLUMNS[:8])

		if not dataframe.empty:
			dataframe["Engagement_Rate"] = [
				((likes + comments) / views * 100.0) if views else 0.0
				for likes, comments, views in zip(
					dataframe["likes"], dataframe["comments"], dataframe["views"]
				)
			]
			dataframe["Like_To_View_Ratio"] = [
				(likes / views) if views else 0.0
				for likes, views in zip(dataframe["likes"], dataframe["views"])
			]
			dataframe["Performance_Category"] = [
				self._categorize_performance(engagement_rate, views)
				for engagement_rate, views in zip(
					dataframe["Engagement_Rate"], dataframe["views"]
				)
			]
		else:
			dataframe["Engagement_Rate"] = pd.Series(dtype="float64")
			dataframe["Like_To_View_Ratio"] = pd.Series(dtype="float64")
			dataframe["Performance_Category"] = pd.Series(dtype="object")

		dataframe["Channel_ID"] = self.channel.channel_id
		dataframe["Channel_Name"] = self.channel.channel_name
		dataframe["Subscribers"] = self.channel.subscribers
		return dataframe.reindex(columns=self._DATAFRAME_COLUMNS)

	def generate_learning_recommendations(
		self,
		target_topic: str,
		max_duration_mins: Union[int, float],
	) -> List[Dict[str, object]]:
		"""Create an ordered learning pathway from matching videos.

		Videos are selected when their topic matches ``target_topic``
		(case-insensitive exact match) and their duration does not exceed the
		requested limit. The pathway ranks them by engagement rate, then view
		count, both descending. Each result includes its sequence number and the
		metrics a student can use to choose a lesson.

		Args:
			target_topic: Topic or learning level to match, such as
				``"Intermediate"``.
			max_duration_mins: Maximum permitted video duration in minutes.

		Returns:
			A list of recommendation dictionaries ordered from strongest to
			weakest engagement. An empty list means no videos matched.

		Raises:
			TypeError: If the topic or duration has an unsupported type.
			ValueError: If the topic is blank or duration is negative/non-finite.
		"""
		if not isinstance(target_topic, str):
			raise TypeError("target_topic must be a string")
		if not target_topic.strip():
			raise ValueError("target_topic cannot be blank")
		if isinstance(max_duration_mins, bool) or not isinstance(
			max_duration_mins, (int, float)
		):
			raise TypeError("max_duration_mins must be a number")
		if not math.isfinite(max_duration_mins) or max_duration_mins < 0:
			raise ValueError("max_duration_mins must be finite and non-negative")

		requested_topic = target_topic.strip().casefold()
		maximum_duration_sec = max_duration_mins * 60
		matches = [
			video
			for video in self.channel.videos
			if video.topic.casefold() == requested_topic
			and video.duration_sec <= maximum_duration_sec
		]
		matches.sort(
			key=lambda video: (
				video.calculate_engagement_rate(),
				video.views,
			),
			reverse=True,
		)

		return [
			{
				"step": index,
				"video_id": video.video_id,
				"title": video.title,
				"topic": video.topic,
				"duration_mins": video.duration_sec / 60.0,
				"views": video.views,
				"engagement_rate": video.calculate_engagement_rate(),
			}
			for index, video in enumerate(matches, start=1)
		]

	def generate_podcast_playlist_recommendation(
		self,
		target_topic: str,
	) -> List[Dict[str, object]]:
		"""Recommend a curated podcast pathway for a requested topic.

		Videos are matched against their category/topic without case sensitivity
		and ranked by engagement rate (highest first), with view count breaking
		ties. The engagement rate is also included as the engagement score so
		the ranking can be explained transparently during a presentation.

		Args:
			target_topic: Category such as ``"Psychology & Focus"`` or
				``"Business & Growth"``.

		Returns:
			An ordered list of episode recommendations with ranking and metrics.
		"""
		if not isinstance(target_topic, str):
			raise TypeError("target_topic must be a string")
		if not target_topic.strip():
			raise ValueError("target_topic cannot be blank")

		requested_topic = target_topic.strip().casefold()
		matches = [
			video
			for video in self.channel.videos
			if video.topic.casefold() == requested_topic
		]
		matches.sort(
			key=lambda video: (
				video.calculate_engagement_rate(),
				video.views,
			),
			reverse=True,
		)

		return [
			{
				"step": index,
				"video_id": video.video_id,
				"title": video.title,
				"topic": video.topic,
				"duration_mins": video.duration_sec / 60.0,
				"views": video.views,
				"engagement_rate": video.calculate_engagement_rate(),
				"engagement_score": video.calculate_engagement_rate(),
				"performance_category": self._categorize_performance(
					video.calculate_engagement_rate(), video.views
				),
			}
			for index, video in enumerate(matches, start=1)
		]

	def export_to_csv(self, filename: str = "yt_analytics.csv") -> str:
		"""Export the analyzed video dataset as a Power BI-friendly CSV.

		The exported file includes original video fields, derived metrics, and
		channel metadata. The dataframe index is omitted because each video
		already has a stable ``video_id`` column.

		Args:
			filename: Destination path. Defaults to ``yt_analytics.csv`` in the
				current working directory.

		Returns:
			The filename written.
		"""
		self.compute_metrics_dataframe().to_csv(filename, index=False)
		return filename

	@classmethod
	def _categorize_performance(cls, engagement_rate: float, views: int = 0) -> str:
		"""Map engagement and views to the requested podcast performance tier."""
		if (
			engagement_rate > cls.VIRAL_ENGAGEMENT_THRESHOLD
			or views > cls.VIRAL_VIEW_THRESHOLD
		):
			return "Viral Hit"
		if engagement_rate >= cls.HIGH_ENGAGEMENT_THRESHOLD:
			return "High Engagement"
		return "Steady Growth"
