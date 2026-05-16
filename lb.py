import requests
import time
from database import cauta_lb_similar_in_cache, salveaza_lb_similar
from lfm import get_artist_top_tracks
LB_URL = "https://api.listenbrainz.org/1/"
USER_AGENT = "Echo/1.0 (http://localhost:5000)"
LB_LABS_URL = "https://labs.api.listenbrainz.org/"

def _request_lb(endpoint, parametri=None):
    if parametri is None:
        parametri = {}
    header = {'User-Agent' : USER_AGENT}
    try:
        raspuns = requests.get(LB_URL + endpoint, params=parametri, headers=header, timeout=10)
    except requests.exceptions.Timeout:
        return None

    if raspuns.status_code!=200:
        return None
    return raspuns.json()


def get_similar_artists(artist_mbid, limit=5):
    #cere artisti similari pentru un mbid dat
    cached = cauta_lb_similar_in_cache(artist_mbid, max_varsta_zile=30)
    if cached is not None:
        print(f"[CACHE HIT LB] similar artists: {artist_mbid}")
        return cached[:limit]
    print(f"[CACHE MISS LB] similar artists : {artist_mbid}")

    parametri = {
        'artist_mbids' : artist_mbid,
        'algorithm': 'session_based_days_7500_session_300_contribution_5_threshold_10_limit_100_filter_True_skip_30'
    }

    header = {'User-Agent' : USER_AGENT}
    try:
        raspuns = requests.get(LB_LABS_URL + 'similar-artists/json', params=parametri, headers=header, timeout=10)
    except requests.exceptions.Timeout:
        return []
    
    if raspuns.status_code!=200:
        return []
    
    data = raspuns.json()
    if not isinstance(data, list):
        return []
    salveaza_lb_similar(artist_mbid, data)
    return data[:limit]


def get_lb_reccs(artist_mbid, nr_artisti=5, piese_per_artist=3):
    data = get_similar_artists(artist_mbid=artist_mbid, limit=nr_artisti)
    if not data:
        return []
    rez = []
    for artist in data:
        if not artist.get('artist_mbid'):
            continue
        rez.extend(get_artist_top_tracks(artist['artist_mbid'], limit=piese_per_artist))
    return rez

