import requests
import os 
from dotenv import load_dotenv
from sp_trck import formateaza_durata
from database import cauta_track_info_in_cache, salveaza_track_info, cauta_similar_in_cache, salveaza_similar
import time as time_module
from concurrent.futures import ThreadPoolExecutor
from mb import filtreaza_genuri, incarca_genuri_mb, normalizeaza_gen

load_dotenv()
_genuri_set_norm = incarca_genuri_mb()

LASTFM_URL = "http://ws.audioscrobbler.com/2.0/"

def _request_lastfm(parametri):
    parametri['format'] = 'json'
    parametri['api_key'] = os.getenv('LASTFM_ID')

    try:
        raspuns = requests.get(LASTFM_URL, params=parametri, timeout=5)
    except requests.exceptions.Timeout:
        return None
    
    if raspuns.status_code != 200:
        return None
    return raspuns.json()


def get_similar_tracks(nume_piesa, nume_artist, limit=20):
    #1. cheia pt cache
    cheie = f"{nume_artist.lower().strip()}|{nume_piesa.lower().strip()}"

    #2. verificare cached
    cached = cauta_similar_in_cache(cheie, max_varsta_zile=7)
    if cached is not None:
        print(f"[CACHE HIT] similar: {cheie}")
        return cached   
    print(f"[CACHE MISS] similar: {cheie}")

    parametri = {
        'method' : 'track.getSimilar',
        'track' : nume_piesa,
        'artist' : nume_artist,
        'limit' : str(limit)
    }

    data = _request_lastfm(parametri=parametri)
    if data is None:
        return []
    
    piese_brute = data.get("similartracks", {}).get("track", [])

        
    
    rez = []
    for piesa in piese_brute:
        name = piesa.get('name', 'Unkown')

        artist_dict = piesa.get('artist', {})
        nume_artist_gasit = artist_dict.get('name', 'Unknown')

        match = float(piesa.get('match', 0))
        url = piesa.get('url', '#')

        imagini = piesa.get('image', [])
        imagine_url = ''
        if len(imagini) > 1:
            imagine_url = imagini[1].get('#text', '')
        
        playcount = int(piesa.get('playcount', 0))
        mbid = piesa.get('mbid', '')

        piese_cr = {
            'name' : name,
            'artist' : nume_artist_gasit,
            'match' : match,
            'url' : url,
            'image' : imagine_url,
            'playcount' : playcount,
            'mbid' : mbid    
        }

        rez.append(piese_cr)
    
    salveaza_similar(cheie, rez)    
    return rez



def get_track_info(nume_piesa, nume_artist):
    #1. construim cheia de cache
    cheie = f"{nume_artist.lower().strip()}|{nume_piesa.lower().strip()}"

    #2. verificam cacheul
    cached = cauta_track_info_in_cache(cheie, max_varsta_zile=7)
    if cached is not None:
        print(f"[CACHE HIT] track_info: {cheie}")
        return cached
    print(f"[CACHE MISS] track_info: {cheie}")


    parametri = {
        'method' : 'track.getInfo',
        'track' : nume_piesa,
        'artist' : nume_artist
    }

    data = _request_lastfm(parametri=parametri)
    if data is None:
        return None
    
    piesa = data.get("track", {})
    if not piesa:
        return None
    
    nume = piesa.get('name', 'Unknown')

    artist_dict = piesa.get('artist', {})
    nume_artist_gasit = artist_dict.get('name', 'Unknown')
    artist_mbid_gasit = artist_dict.get('mbid', '')

    album = piesa.get('album', {}).get('title', 'Unknown')
    duration_ms = int(piesa.get('duration', 0))
    duration = formateaza_durata(duration_ms)
    listeners = int(piesa.get('listeners', 0))
    playcount = int(piesa.get('playcount', 0))
    image = piesa.get('album', {}).get('image', [])
    imagine_url = ''
    if len(image) > 3:
            imagine_url = image[3].get('#text', '')

    tags = piesa.get('toptags', {}).get('tag', [])
    if isinstance(tags, dict):
        tags = [tags]
    tags_final = []
    for tag in tags:
        tags_final.append(tag.get('name', ''))

    summary = piesa.get('wiki', {}).get('summary', '')

    rezult = {
        'name' : nume,
        'artist' : nume_artist_gasit,
        'artist_mbid' : artist_mbid_gasit,
        'album' : album,
        'duration' : duration,
        'listeners' : listeners,
        'playcount' : playcount,
        'image' : imagine_url,
        'tags' : tags_final,
        'summary' : summary,
        'mbid' : piesa.get('mbid', '')
    }

    salveaza_track_info(cheie, rezult)
    return rezult
    

def get_artist_info(nume_artist):
    parametri = {
        'method' : 'artist.getInfo',
        'artist' : nume_artist
    }

    date = _request_lastfm(parametri)
    if date is None:
        return None
    
    artist_data = date.get('artist', {})
    if not artist_data:
        return None
    
    nume = artist_data.get('name', 'Unknown')
    mbid = artist_data.get('mbid', '')
    url = artist_data.get('url', '#')

    image = artist_data.get('image', [])
    imagine_url = ''
    if len(image) > 3:
            imagine_url = image[3].get('#text', '')

    stats = artist_data.get('stats', {})
    listeners = int(stats.get('listeners', 0))
    playcount = int(stats.get('playcount', 0))

    bio_summary = artist_data.get('bio', {}).get('summary', '')

    tags = artist_data.get('tags', {}).get('tag', [])
    if isinstance(tags, dict):
        tags = [tags]
    final_tags = []
    for tag in tags:
        final_tags.append(tag.get('name', ''))

    similar = artist_data.get('similar', {}).get('artist', [])
    if isinstance(similar, dict):
        similar = [similar]
    final_similar = []
    for sim in similar:
        final_similar.append(sim.get('name', ''))

    return {
        'name' : nume,
        'mbid' : mbid,
        'url' : url,
        'image' : imagine_url,
        'listeners' : listeners,
        'playcount' : playcount,
        'tags' : final_tags,
        'similar_artists' : final_similar,
        'bio_summary' : bio_summary
    }


def reordoneaza_similar(piesa, artist, lista_lastfm, lista_lb=None):
    """
    Combină recomandări Last.fm + ListenBrainz, calculează scor și sortează.
    """
    if lista_lb is None:
        lista_lb = []
    
    # 1 - amprenta de gen a peisei
    info_originala = get_track_info(piesa, artist)
    if not info_originala or not info_originala.get('tags'):
        amprenta_originala = set()
    else:
        tags_originala = [tag.lower() for tag in info_originala['tags']]
        amprenta_originala = set(normalizeaza_gen(t) for t in filtreaza_genuri(tags_originala, _genuri_set_norm))
    
    #2- construim un dict unificat cu toate piesele 
    toate_piesele = {}
    
    for rec in lista_lastfm:
        cheie = rec.get('name', '').lower().strip()
        toate_piesele[cheie] = {
            'rec': rec,
            'in_lastfm': True,
            'in_lb': False
        }
    
    for rec in lista_lb:
        cheie = rec.get('name', '').lower().strip()
        if cheie in toate_piesele:
            # apare in ambele surse
            toate_piesele[cheie]['in_lb'] = True
        else:
            toate_piesele[cheie] = {
                'rec': rec,
                'in_lastfm': False,
                'in_lb': True
            }
    
    #3- pentru fiecare piesa calculeaza scor
    def proceseaza_o_piesa(item_tuple):
        """Procesează o singură piesă - calculează scor."""
        cheie, item = item_tuple
        rec = item['rec']
        rec_name = rec.get('name', '')
        rec_artist = rec.get('artist', '')
        
        cheie_cache = f"{rec_artist.lower().strip()}|{rec_name.lower().strip()}"
        cached = cauta_track_info_in_cache(cheie_cache, max_varsta_zile=7)
        if cached is not None:
            info_rec = cached
        else:
            info_rec = get_track_info(rec_name, rec_artist)
        
        if info_rec and info_rec.get('tags'):
            tags_rec = [tag.lower() for tag in info_rec['tags']]
            amprenta_rec = set(normalizeaza_gen(t) for t in filtreaza_genuri(tags_rec, _genuri_set_norm))
        else:
            amprenta_rec = set()
        
        if not amprenta_rec:
            tags_artist = get_artist_tags(rec_artist)
            if tags_artist:
                amprenta_rec = set(normalizeaza_gen(t) for t in filtreaza_genuri(tags_artist, _genuri_set_norm))
        overlap = len(amprenta_originala & amprenta_rec)
        match_lastfm = rec.get('match', 0)
        bonus_cross = 5 if (item['in_lastfm'] and item['in_lb']) else 0
        scor_final = overlap * 10 + bonus_cross + match_lastfm
        
        return {
            'recomandare': rec,
            'scor': scor_final,
            'overlap': overlap,
            'in_ambele': item['in_lastfm'] and item['in_lb']
        }

    # procesare paralela
    with ThreadPoolExecutor(max_workers=3) as executor:
        recomandari_cu_scor = list(executor.map(proceseaza_o_piesa, toate_piesele.items()))
    
    recomandari_cu_scor = [
        item for item in recomandari_cu_scor
        if not (item['overlap'] == 0 and not item['in_ambele'] and item['recomandare'].get('source') == 'listenbrainz')
    ]
    for item in recomandari_cu_scor:
        rec = item['recomandare']
        print(f"  {rec.get('name')} - {rec.get('artist')} | scor: {item['scor']:.2f} | overlap: {item['overlap']} | cross: {item['in_ambele']}")
    # sorteaza dupa scor descrescator
    recomandari_cu_scor.sort(key=lambda x: x['scor'], reverse=True)

    max_overlap = max((item['overlap'] for item in recomandari_cu_scor), default=1)
    if max_overlap == 0:
        max_overlap = 1
    amprenta_goala = len(amprenta_originala) == 0
    recomandari_finale = []
    for item in recomandari_cu_scor:
        rec = item['recomandare']
        rec['overlap'] = item['overlap']
        if amprenta_goala:
            match_value = rec.get('match', 0)
            scor = round(match_value * 100)
            rec['similarity_score'] = max(scor, 1)
        else:
            rec['similarity_score'] = round((item['overlap'] / max_overlap) * 100)
        recomandari_finale.append(rec)

    #max 3 piese / artist
    lista_finala = []
    contor_artisti = {}
    for piesa in recomandari_finale:
        artist = piesa['artist'].lower()
        contor_artisti[artist] = contor_artisti.get(artist, 0) + 1
        if contor_artisti[artist] <= 3:
            lista_finala.append(piesa)
    return lista_finala
    
    

def get_artist_top_tracks(artist_mbid, limit=5):
    # ia top piesele unui artist de la lastfm folosind mbid

    parametri = {
        'method' : 'artist.getTopTracks',
        'mbid' : artist_mbid,
        'limit' : limit
    }
    raspuns = _request_lastfm(parametri=parametri)
    if raspuns is None:
        return []
    
    tracks_r = raspuns.get('toptracks', {}).get('track', [])
    if isinstance(tracks_r, dict):
        tracks_r = [tracks_r]

    rez = []
    for piesa in tracks_r:
        artist_dict = piesa.get('artist', {})
        nume_artist = artist_dict.get('name', 'Unknown')

        rez.append({
            'name' : piesa.get('name', 'Unknown'),
            'artist' : nume_artist,
            'url' : piesa.get('url', ''),
            'image' : '',
            'playcount' : int(piesa.get('playcount', 0)),
            'match' : 0.0,
            'source' : 'listenbrainz'
        })
    return rez

def get_artist_tags(artist_name):
    """Tag-uri Last.fm ale unui artist."""
    parametri = {
        'method': 'artist.getTopTags',
        'artist': artist_name
    }
    data = _request_lastfm(parametri)
    if data is None:
        return []
    tags_raw = data.get('toptags', {}).get('tag', [])
    return [t['name'].lower() for t in tags_raw[:10] if int(t.get('count', 0)) > 0]




    