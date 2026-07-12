from flask import Flask, render_template, request
from sp_trck import search_track, get_track_by_id
from auth import get_spotify_token
from database import setup_database, cauta_in_cache, salveaza_cautare, cauta_homepage_track_in_cache, salveaza_homepage_track
from rate_lim import permite_cerere, curata_ipuri_vechi
from lfm import get_track_info, get_similar_tracks, get_tag_top_tracks
from sp_trck import enrich_spotify_images
from lfm import reordoneaza_similar
from flask import jsonify
from itunes import get_preview_itunes
import random
import time
app = Flask(__name__)
setup_database()
_ultima_curatare = time.time()


PIESE = [
    "1wl53ydLl7vh2t7bFMZ5dn",
    "5qiLqf4uN3jldGTFb2W7rH",
    "0y9NSQUOROIidcOFc3zJ00",
    "0SSgFHwFOi2HNrBgnPDc3P",
    "4qorQTHgJZ4bmeCORA2zQU",
    "0fKzRLl4kIG8LQikoG1bvb",
    "3nkdVXnH4xC6f3YZS0C8pC",
    "66qzEsdBWD9BmgvTuztEfc",
    "6WRt3zMQLxqt4RtwzTz2TO",
    "2CT85N0Rwl2UtNOYZ4gepm",
    "7feFMZxaNV6km5QZAXYyv0",
    "5x9PIacjaOGqcQkmiQBfKG",
    "0kSmBFytVCj0POoAQCFWTK",
    "5gn7mMDHaVMrWGKVMbaSfS",
    "0J6GmECIOeztIZhdqJ2RaA",
    "18YikwS69KGuELmDLwhHsD",
    "3a8H9SY7zTGJt5h4679dPy",
    "73nifoOJDzdl69R9E96RQa",
    "2ap04UmehNhJ23Gu9Vnd0Z",
    "1V9ZOxFFsKUd2ZpY2DKSZR",
    "32hGR5QuiPmhAdBxsmEUxw",
    "26tQBNLe0ByJgtZzcEMHls",
    "2CAVnk831e6jat8lnXk8KX",
    "2BCw5RBr7KnJHPZ6xNnW7C",
    "1joiQBvqLuivn9JJyxBXco",
    "2lzwJjDENCMGBY2cR4ksME",
    "3Jd6G5xoykZ9IA2LOuQrGh",
    "6RvDmpY1Vv8iNs5EZ4IFg6",
    "3ps6s8ojt0ttbKFEj7fuP7",
    "2C014cVoBciAu3NFRoJpQk",
    "2OyuxmGylAORg6KIdSdnGQ",
    "5UiJKkkSBr4rL31pO5KmPP",
    "1I2oeu3krO4fifSVVl0zl3",
    "4bNlqkHxoF3ViKZwDAjRA2",

    "6ioHOIVulSRPn0MMfxQcWS",
    "2aKd630BXs24Yt1znAty7Z",
    "2zBoF0o8bsUlVUS2ok41RV",
    "2DqNos0X1deEguTxMMW8UW",
    "20FvZSnULuxXSq25w9k6Ov",
    "1bujdcYDzWPyJHUiL6PXul",
    "5tLSfxJJNjJOyME802bRUF",
    "0uPa1nW3fgWcW8RsMbkRUp",
    "1rP8xYO8cMuFtEIzc20u5z",
    "6JtcpkQ3K3GqtXi5mNKu9m",
    "4k5kRgUxVcT6dCl1c45X6r",
    "17PAfAyPL4NTbRBidZWo2w",
    "3bvMJNoRWMtUHwUsMCkYGi",
    "0PriHsz5yHbgFxL4w9Cu98",
    "7160xh2axCP5iF3GpZxsjX",
    "2wvvFDzDUGprLYIVFPxomd",
    "1pXB6sODqCvLcq1CGDEISC",
    "01uhNrw9VBZMbAiolACMwA",
    "6Hm4wPMF1yDoLDe3hwvWQB",
    "7mWERi6gyXvxfYxrb0exlm",
    "0u6SJZRhC1KSguPxLACkt9",
    "7iYREEy6XYMjVx2OjMqrVi",
    "30EzorNyMMjPkgNzkRzeVD",
    "5m3Uzjuiyj8656EGM1bwhk",
    "7l4vPBIG4SdD5dEIMwM46f",
    "3kkwWy8dBPjNooy0PZgNKz",
    "0yZcpNx3DddOzQB3uxVq1q",
    "16HnkYl3bGv89Dg3gEQWcj",
    "2P43WROXRRBFqSKd2aSc0o",
    "29jQiEMxUhnQMfCQp7Yiai",
    "5bFXSB4ouW7vAUXyoRaGAm",
    "6tAifEQOTqHMw8mTvAJsPY",
    "1HIhfI88cgtRStC5qWHXpz",
    "0keKatmlSsJqMlO134bPVA",
    "43XhVURnMNKXlFdXuzmiW2",
    "0VNjaRcmIowjLbPtYDhLuh",
    "3VBRUO4wjD9QYQCISZnfYS",
    "5T7UCVgoL0fcTvcVekO5gS",
    "7AxIe6tbdJQ7ifQoHGImTJ",
    "1c2gssCkuT9RMn0WXFiDps",
    "4L4zDLCJAVWz7R0lE6VtBG",
    "0UonqIHYazAtZvAptzuXKZ",
    "77bnW7cdNfWIu9uq2kjz8C",
    "2uCLqFpSdVXmtsMLSFDrvw",
    "3WtVG4kC6xHQTwAXGmEvI3",
    "2bYJIMEvnrcGfE6y3XaRJd",
    "4k2TKhns1c2Tkcf5MYLHtp",
    "36BcBleg7Sgzc54xMPwimr",
    "5lbOkABADpqP9wl5hS8Ifn",
    "012HXCZBt8IDDIP8brJetj",
    "0LoyvHuqMPhB7Xh9aXa4RC",
    "3s1aD2AxCHddWZQEsOrj9l",
    "72iI6qd5HZqpXPzY74b7xi",
    "1jSx3gXOde9A1EgjafH8Vc",
    "0Vn8DjozlIroAUJrKU24cr",
    "1o84U3oManq1ink1jpJS1x",
    "6ZMkAikyRQS9Y87slvJaKw",
    "5I0IWGBtCtrQEO7Z2j83ko",
    "502L6h1n5XNR8zflhkxMjP",
    "0WQFibrfeHPwrHQE0STL4d",
    "0hW9s6E4i6NMLCR7CJdgwn",
    "4QAzybZo9lt86NI9OFFTS5",
    "7DT9NUuPdrxKHvg62JbqJm",
    "0RlpgTdnxatoTRBvG34zaB",
    "1ronXaZSfVgGH0RuN9MIOM",
    "2IuwQFxfEhtoQVDyhEUtfq",
    "3290xgMPKnbNjAu9Bd1CvN",
    "6h7Vea8KZZtHFHEmolAuBF",
    "5EDAsXfSa1LpsTjbe4GbgY",
    "258A9AqIO57XY9BrAgwpEt",
    "2K3YgHwfo1iNucwa5hVGSW",
    "3LqZhe0pkxDCIHH0eQabDv",
    "7sh5vtisZIFk8IPfnWIYgE",
    "4JD1CS0yfo9EXHOZbc0eKo",
    "1mrkmgW1Eq6ve8bP4ResOa",
    "59Z6lTartoVyw6d69RfcBY",
    "1BuNvm62gxJ11xdq3SWhnu",
    "2rRrV0syrGGaVbVDHXESs3"
]

GENURI = [
    "hyperpop", "chillwave", "glitch pop", "emo", "dub techno",
    "ambient", "shoegaze", "post-hardcore", "screamo", "vaporwave",
    "dream pop", "witch house", "breakcore", "art pop", "electropop",
    "indie pop", "downtempo", "trip hop", "darkwave", "midwest emo",
    "slowcore", "post-rock", "noise pop", "bedroom pop", "hexd"
]

def get_genuri_shuffle(n=7):
    return random.sample(GENURI, min(n, len(GENURI)))

def get_homepage_tracks(n = 10):
    alese = random.sample(PIESE, min(n, len(PIESE)))

    piese = []
    token = None

    for sid in alese:
        cached = cauta_homepage_track_in_cache(sid, max_varsta_zile=30)
        if cached is not None:
            piese.append(cached)
            continue

        if token is None:
            token = get_spotify_token()
        t = get_track_by_id(sid, token)
        if t:
            salveaza_homepage_track(sid, t)
            piese.append(t)

    return piese

@app.route('/', methods=['GET', 'POST'])
def index():

    global _ultima_curatare
    timp_trecut = time.time() - _ultima_curatare
    if timp_trecut > 300:
        curata_ipuri_vechi()
        _ultima_curatare = time.time()

    if request.method == 'POST':
        ip = request.remote_addr
        if not permite_cerere(ip):
            return render_template('index.html', error="Too many searches at once.", query=request.form.get('search_query', ''))
        
        text = request.form.get('search_query', '').strip()
        
        if not text:
            return render_template('index.html')
        
        #1 - verifica cacheul
        rezultate_cache = cauta_in_cache(text, max_varsta_zile=7)
        
        if rezultate_cache is not None:
            print(f"Cache HIT pentru: {text}")
            return render_template('index.html', results=rezultate_cache, query=text)
        
        #2 - daca nu e in cache se intreaba spotify
        print(f"Cache MISS pentru: {text} - intrebam Spotify")
        
        try:
            spotify_token = get_spotify_token()
            print(f"[DEBUG] token primit: {str(spotify_token)[:15]}")
            rezultate = search_track(text, spotify_token)
        except Exception as e:
            print(f"Eroare la Spotify: {e}")
            rezultate = []

        from sp_trck import rate_limited, _spotify_block
        if not rezultate and rate_limited:
            ramas_min = max(1, int((_spotify_block - time.time()) / 60))
            return render_template('index.html', error=f"Temporary unavailable(too many requests). Try again in ~{ramas_min}.", query=text)
        
        #3 - daca sunt rezultate se salveaza in cache
        if rezultate:
            salveaza_cautare(text, rezultate)
        
        return render_template('index.html', results=rezultate, query=text)
    
    piese_homepage = get_homepage_tracks(n=10)
    genuri_sdbar = get_genuri_shuffle(n=7)
    return render_template('index.html', piese_homepage=piese_homepage, genuri_sdbar=genuri_sdbar)

@app.route('/track/<spotify_id>')
def track_detail(spotify_id):
    #1 - verifica rate limit
    ip = request.remote_addr
    if not permite_cerere(ip):
        return render_template('track.html', error="Too many requests.")
    
    #2- ia detaliile piesei
    spotify_token = get_spotify_token()
    track_basic = get_track_by_id(spotify_id, spotify_token)
    
    if track_basic is None:
        return render_template('track.html', error="Track not found.")
    
    #3- ia info de la lastfm
    lastfm_info = get_track_info(track_basic['name'], track_basic['artist'])

    preview_url = get_preview_itunes(track_basic["artist"], track_basic["name"])
    
    #4- ia recomandari de la lastfm
    #similare = get_similar_tracks(track_basic['name'], track_basic['artist'], limit=20)

    #similare = reordoneaza_similar(track_basic['name'], track_basic['artist'], similare)

    #if similare:
        #similare = enrich_spotify_images(similare, spotify_token)
    
    return render_template(
        'track.html',
        track=track_basic,
        preview_url=preview_url,
        lastfm=lastfm_info,
        #similare=similare
        similare=[]
    )

@app.route('/api/similar/<spotify_id>')
def api_similar(spotify_id):
    t0 = time.time()
    token = get_spotify_token()
    track_basic = get_track_by_id(spotify_id, token)
    print(f"[TIMING] get_track_by_id : {time.time() - t0:.2f}s")
    
    if not track_basic:
        return jsonify([])
    
    t1 = time.time()
    similare = get_similar_tracks(track_basic['name'], track_basic['artist'], limit=20)
    print(f"[TIMING] get_similar_tracks: {time.time()-t1:.2f}s")
    print(f"[DEBUG] Last.fm similar: {len(similare)} piese")

    t2 = time.time()
    lastfm_info = get_track_info(track_basic['name'], track_basic['artist'])
    print(f"[TIMING] get_track_info original: {time.time()-t2:.2f}s")
    print(f"[DEBUG] artist_mbid: '{lastfm_info.get('artist_mbid') if lastfm_info else 'N/A'}'")

    t3 = time.time()
    similare_lb = []
    if lastfm_info and lastfm_info.get('artist_mbid'):
        from lb import get_lb_reccs
        similare_lb = get_lb_reccs(lastfm_info['artist_mbid'], nr_artisti=5, piese_per_artist=3)
    print(f"[TIMING] get_lb_reccs: {time.time()-t3:.2f}s")

    t4 = time.time()
    similare = reordoneaza_similar(track_basic['name'], track_basic['artist'], similare, similare_lb)
    print(f"[TIMING] reordoneaza_similar: {time.time()-t4:.2f}s")

    t5 = time.time()
    similare = similare[:20]
    similare = enrich_spotify_images(similare, token)
    print(f"[TIMING] enrich_spotify_images: {time.time()-t5:.2f}s")
    
    print(f"[TIMING] TOTAL: {time.time()-t0:.2f}s")
    return jsonify(similare)

@app.route('/api/track-info/<spotify_id>')
def api_track_info(spotify_id):
    token = get_spotify_token()
    track_basic = get_track_by_id(spotify_id, token)

    if not track_basic:
        return jsonify({})
    
    lastfm_info = get_track_info(track_basic['name'], track_basic['artist'])

    rez = {
        'recording' : None,
        'artist' : None
    }

    if lastfm_info:
        if lastfm_info.get('mbid'):
            from mb import get_recording_info
            rez['recording'] = get_recording_info(lastfm_info['mbid'])
        if lastfm_info.get('artist_mbid'):
            from mb import get_artist_details
            rez['artist'] = get_artist_details(lastfm_info['artist_mbid'])
    return jsonify(rez)

@app.route("/tag/<nume_tag>")
def tag_page(nume_tag):
    piese = get_tag_top_tracks(nume_tag, limit=50)

    return render_template(
        'tag.html',
        tag=nume_tag,
        piese=piese
    )
    





if __name__ == '__main__':
    import os
    debug_mode = os.getenv('FLASK_DEBUG', 'False') == 'True'
    app.run(debug=debug_mode)


