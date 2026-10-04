# analytics-system-project_OOAD

Fetched channel and video records are stored in `youtube_analytics.db` using
SQLite. Running `main.py` creates the database if needed and inserts or updates
the fetched records in the `channels` and `videos` tables. The analytics export
continues to be written to `yt_analytics.csv` for spreadsheet and Power BI use.