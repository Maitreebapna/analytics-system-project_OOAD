"""Shared data refresh workflow for the CLI and web API."""

from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import pandas as pd

from analytics import AnalyticsEngine
from database import YouTubeDatabase
from fetcher import YouTubeDataFetcher
from models import Channel


PROJECT_DIR = Path(__file__).resolve().parent
DATABASE_PATH = PROJECT_DIR / "youtube_analytics.db"
CSV_PATH = PROJECT_DIR / "yt_analytics.csv"


@dataclass
class RefreshResult:
	channel: Channel
	dataframe: pd.DataFrame
	data_source: str
	fallback_reason: Optional[str]
	snapshot_id: int


def refresh_data(channel_id: Optional[str] = None) -> RefreshResult:
	"""Fetch data, compute metrics, save a snapshot, and refresh the CSV export."""
	fetcher = YouTubeDataFetcher()
	channel = fetcher.fetch_channel_data(channel_id)
	dataframe = AnalyticsEngine(channel).compute_metrics_dataframe()
	database = YouTubeDatabase(str(DATABASE_PATH))
	snapshot_id = database.save_snapshot(
		channel,
		dataframe.to_dict(orient="records"),
		fetcher.data_source,
	)
	dataframe.to_csv(CSV_PATH, index=False)
	return RefreshResult(
		channel=channel,
		dataframe=dataframe,
		data_source=fetcher.data_source,
		fallback_reason=fetcher.fallback_reason,
		snapshot_id=snapshot_id,
	)