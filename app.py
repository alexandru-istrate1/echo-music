from flask import Flask, render_template, request
from sp_trck import search_track, get_track_by_id
from auth import get_spotify_token
from database import setup_database, cauta_in_cache, salveaza_cautare
from rate_lim import permite_cerere, curata_ipuri_vechi
from lfm import get_track_info, get_similar_tracks
from sp_trck import enrich_spotify_images
from lfm import reordoneaza_similar
from flask import jsonify
from itunes import get_preview_itunes
import time
app = Flask(__name__)
setup_database()
_ultima_curatare = time.time()

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
            rezultate = search_track(text, spotify_token)
        except Exception as e:
            print(f"Eroare la Spotify: {e}")
            rezultate = []
        
        #3 - daca sunt rezultate se salveaza in cache
        if rezultate:
            salveaza_cautare(text, rezultate)
        
        return render_template('index.html', results=rezultate, query=text)
    
    
    return render_template('index.html')

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

    t2 = time.time()
    lastfm_info = get_track_info(track_basic['name'], track_basic['artist'])
    print(f"[TIMING] get_track_info original: {time.time()-t2:.2f}s")

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

if __name__ == '__main__':
    app.run(debug=True)