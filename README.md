# analytics-system-project_OOAD

YouTube channel data is fetched from the YouTube Data API when an API key is
configured. Without a key, the project uses clearly labeled illustrative mock
data. Each run analyzes the videos, updates the current records in SQLite, adds
a dated analytics snapshot, and exports a Power BI-friendly CSV.

## Setup and Run

Use PowerShell from the project directory:

```powershell
.\myenv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python main.py
```

If PowerShell blocks virtual-environment activation, run this once in the same
terminal before activating:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned
```

To use live YouTube data, set an API key in the current PowerShell session
before running the program:

```powershell
$env:YOUTUBE_API_KEY = "your-api-key"
python main.py
```

The channel can optionally be changed with `YOUTUBE_CHANNEL_ID`. If the API
request fails or the channel is not found, the run reports why and uses mock
data instead.

## Outputs

Both output files are written beside `main.py`, regardless of the current
terminal directory:

- `youtube_analytics.db`: SQLite tables for current channel/video records and
	dated analytics snapshots. The `powerbi_video_analytics` view combines
	snapshot metadata with the video metrics.
- `yt_analytics.csv`: Latest run, with the existing column names retained for
	compatibility with Power BI reports already connected to this file.

## Power BI

In Power BI Desktop, select **Get Data > Text/CSV**, choose `yt_analytics.csv`,
then select **Load** or **Transform Data**. Refresh the query after each run of
`main.py`. The CSV is the recommended source for an existing dashboard.

For historical trends, connect Power BI to the SQLite database using an
installed SQLite ODBC driver: select **Get Data > ODBC**, choose the DSN pointing
to `youtube_analytics.db`, and select the `powerbi_video_analytics` view. Each
successful run creates another snapshot row set, including whether the source
was live or mock data.

## Tests

Run the command-line analytics pipeline with:

```powershell
python main.py
```

## Web Frontend API

Install the updated dependencies, create or refresh an analytics snapshot, and
start the local API server:

```powershell
python -m pip install -r requirements.txt
python main.py
python -m uvicorn api:app --reload
```

The API listens at `http://127.0.0.1:8000`. Open
`http://127.0.0.1:8000/docs` to try the endpoints interactively. A browser
frontend can call these routes:

- `GET /api/health`: API and snapshot status.
- `GET /api/dashboard`: channel and aggregate metrics for the latest snapshot.
- `GET /api/videos`: latest video metrics; supports `topic`,
	`performance_category`, `search`, `sort_by`, `sort_order`, `limit`, and
	`offset` query parameters.
- `GET /api/recommendations?topic=Psychology%20%26%20Focus`: ordered videos for
	a topic; accepts `max_duration_mins` and optional `channel_id`.
- `POST /api/refresh`: fetch and save a new snapshot. Send `{}` for the
	configured channel or `{"channel_id":"@handle"}` to select a channel.

The default CORS allowlist supports local frontend servers on ports 3000, 5173,
and 5500. For a different origin, set `FRONTEND_ORIGINS` to a comma-separated
list of full origins, such as `http://localhost:8080`. This API is intended for
local development; it does not include authentication or production hosting
configuration.
