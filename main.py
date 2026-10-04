"""Run the YouTube educational content analytics demo."""

import os
from typing import Optional

from analytics import AnalyticsEngine
from fetcher import YouTubeDataFetcher


def main() -> None:
	"""Fetch Raj Shamani data, present podcast analytics, and export a CSV."""
	api_key: Optional[str] = os.getenv("YOUTUBE_API_KEY")
	recommendation_topic = "Psychology & Focus"
	has_api_key = bool(api_key and api_key.strip())

	if has_api_key:
		print("[INFO] Live API Key Found")
	else:
		print("[INFO] No API Key Found - Using Raj Shamani Dataset")

	fetcher = YouTubeDataFetcher(api_key=api_key)
	channel = fetcher.fetch_channel_data("@rajshamani")
	analytics = AnalyticsEngine(channel)

	average_engagement = channel.get_average_engagement()
	dataframe = analytics.compute_metrics_dataframe()
	top_episodes = dataframe.sort_values(
		["Engagement_Rate", "views"],
		ascending=[False, False],
	).head(6)
	recommendations = analytics.generate_podcast_playlist_recommendation(
		recommendation_topic
	)

	print("\n" + "=" * 72)
	print("RAJ SHAMANI | FIGURING OUT PODCAST ANALYTICS")
	print("=" * 72)
	print(f"Channel Name:                 {channel.channel_name}")
	print(f"Total Videos Analyzed:        {len(channel.videos):,}")
	print(f"Average Engagement Rate:      {average_engagement:.2f}%")

	print("\nTOP 6 EPISODES BY ENGAGEMENT RATE")
	if top_episodes.empty:
		print("  No episode data available.")
	else:
		for rank, (_, episode) in enumerate(top_episodes.iterrows(), start=1):
			print(f"  {rank}. {episode['title']}")
			print(
				f"     Engagement: {episode['Engagement_Rate']:.2f}% | "
				f"Views: {episode['views']:,} | Likes: {episode['likes']:,} | "
				f"Comments: {episode['comments']:,} | "
				f"Category: {episode['Performance_Category']}"
			)

	print(f"\nRECOMMENDED LEARNING PATHWAY: {recommendation_topic}")
	if not recommendations:
		print("  No matching episodes found.")
	else:
		for recommendation in recommendations:
			print(
				f"  {recommendation['step']}. {recommendation['title']} "
				f"| Score: {recommendation['engagement_score']:.2f}% "
				f"| Views: {recommendation['views']:,}"
			)

	csv_filename = analytics.export_to_csv("yt_analytics.csv")
	print("\nEXPORT")
	print(f"  Analytics dataset saved to {csv_filename}")


if __name__ == "__main__":
	main()
