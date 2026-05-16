# Echo — Music Discovery Web App

A depth-first music discovery platform — "Wikipedia for music with recommendations."

Unlike Spotify or Last.fm, Echo prioritizes **genre accuracy** and **data depth** over popularity, combining multiple independent sources to deliver better recommendations.

## Features

- **Multi-source recommendations** — Last.fm similarity + ListenBrainz artist-based discovery
- **Genre filtering** — MusicBrainz official taxonomy filters out irrelevant recommendations
- **Cross-validation** — tracks appearing in multiple sources get boosted
- **Smart caching** — 3-level SQLite cache (search, track info, images) with configurable TTL
- **Lazy loading** — page loads instantly, recommendations stream in via AJAX
- **Parallel processing** — concurrent API calls for faster response times

## Tech Stack

- **Backend:** Flask + Python
- **Database:** SQLite
- **APIs:** Spotify, Last.fm, MusicBrainz, ListenBrainz

## Setup

1. Clone the repo
2. Create a virtual environment: `python -m venv venv`
3. Install dependencies: `pip install flask requests python-dotenv`
4. Create `.env` with your API keys
5. Run: `python app.py`

## Status

Work in progress — actively developed.
