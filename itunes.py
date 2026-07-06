import requests

def get_preview_itunes(artist, track):
    url = "https://itunes.apple.com/search"
    params = {
        "term" : f"{artist} {track}",
        "entity" : "song",
        "limit" : 3
    }

    try:
        r = requests.get(url, params=params, timeout=5)
        r.raise_for_status()
        rezultate = r.json().get("results", [])
    except (requests.RequestException, ValueError):
        return None


    for item in rezultate:
        if item.get("previewUrl"):
            return item["previewUrl"]
    return None