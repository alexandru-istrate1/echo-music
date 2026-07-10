import requests

def get_preview_itunes(artist, track):
    url = "https://itunes.apple.com/search"
    params = {
        "term" : f"{artist} {track}",
        "entity" : "song",
        "limit" : 5
    }

    try:
        r = requests.get(url, params=params, timeout=5)
        r.raise_for_status()
        rezultate = r.json().get("results", [])
    except (requests.RequestException, ValueError):
        return None

    artist_cerut = artist.lower().strip()
    for item in rezultate:
        if not item.get("previewUrl"):
            continue
        artist_gasit = item.get("artistName", "").lower().strip()

        if artist_cerut in artist_gasit or artist_gasit in artist_cerut:
            return item["previewUrl"]
    return None