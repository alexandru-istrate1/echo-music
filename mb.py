import requests
import time
import urllib.parse
import os
import json
from database import cauta_artist_mb_in_cache, cauta_recording_in_cache, salveaza_recording_in_cache, salveaza_artist_mb
MB_URL = "https://musicbrainz.org/ws/2/"
USER_AGENT = "Echo/1.0 (http://localhost:5000)"
GENURI_FILE = 'genuri_mb.json'

def _request_mb(endpoint, parametri):
    parametri['fmt'] = 'json'
    time.sleep(1)
    header = {'User-Agent' : USER_AGENT}
    try:
        raspuns = requests.get(MB_URL + endpoint, params=parametri, headers=header, timeout=10)
    except requests.exceptions.Timeout:
        return None
    
    if raspuns.status_code!=200:
        return None
    return raspuns.json()
    
def get_recording_info(mbid):
    #1. verificare cheie cache
    cache = cauta_recording_in_cache(mbid, max_varsta_zile=30)
    if cache is not None:
        print(f"[CACHE HIT MB]")
        return cache
    print(f"[CACHE MISS MB]")

    raspuns = _request_mb(f'recording/{mbid}', {'inc': 'genres+tags+releases+labels'})

    if raspuns is None:
        return None
    
    titlu = raspuns.get('title', 'Unknown')
    
    genuri_extr = raspuns.get('genres', [])
    genuri = []
    for gen in genuri_extr:
        genuri.append(gen['name'])

    tags_extr = raspuns.get('tags', [])
    taguri = []
    for tag in tags_extr:
        taguri.append(tag['name'])


    
    releases_extr = raspuns.get('releases', [])
    releases_extr.sort(key=lambda r: r.get('date', '') or 'zzzz')
    if releases_extr:
        release = releases_extr[0]
        titlu_release = release.get('title', 'Unknown')
        data_lansare = release.get('date', 'Unknown')

        label_info = release.get('label-info', [])
        if label_info:
            label = label_info[0].get('label', {}).get('name', 'Unknown')
        else:
            label = 'Unknown'
    else:
        titlu_release = 'Unknown'
        data_lansare = 'Unknown'
        label = 'Unknown'

    rez = {
        'title' : titlu,
        'genres' : genuri,
        'tags' : taguri,
        'release_title' : titlu_release,
        'release_date' : data_lansare,
        'label' : label
    }

    salveaza_recording_in_cache(mbid, rez)
    return rez


def get_artist_details(mbid):
    cache = cauta_artist_mb_in_cache(mbid, max_varsta_zile=30)
    if cache is not None:
        print("[CACHE HIT MB_ART]")
        return cache
    print("[CACHE MISS MB_ART]")

    raspuns = _request_mb(f'artist/{mbid}', {'inc': 'genres+tags'})

    if raspuns is None:
        return None
    
    nume = raspuns.get('name', 'Unknown')
    tip = raspuns.get('type', 'Unknown')
    tara = raspuns.get('country', 'Unknown')
    time_begin = raspuns.get('life-span', {}).get('begin', 'Unknown')
    time_end = raspuns.get('life-span', {}).get('end', 'Unknown')

    genuri_extr = raspuns.get('genres', [])
    genuri = []
    for gen in genuri_extr:
        genuri.append(gen['name'])

    
    taguri_extr = raspuns.get('tags', [])
    taguri = []
    for tag in taguri_extr:
        taguri.append(tag['name'])

    rez = {
        'name' : nume,
        'type' : tip,
        'country' : tara,
        'begin' : time_begin,
        'end' : time_end,
        'genres' : genuri,
        'tags' : taguri
    }

    salveaza_artist_mb(mbid, rez)
    return rez


def descarca_genuri():
    toate_genurile = []
    offset = 0
    limit = 100
    while True:
        raspuns = _request_mb('genre/all', {'limit' : str(limit), 'offset' : str(offset) })

        if raspuns is None:
            break
        lista = raspuns.get('genres', [])
        for gen in lista:
            toate_genurile.append(gen['name'])
        if len(lista) < limit:
            break
        else:
            offset+=limit
    
    with open(GENURI_FILE, 'w') as f:
        json.dump(toate_genurile, f)
    print(f"Salvate {len(toate_genurile)} genuri în {GENURI_FILE}")
    return toate_genurile

def normalizeaza_gen(gen):
    return gen.replace('-', '').replace(' ', '').lower()

def incarca_genuri_mb():
    if not os.path.exists(GENURI_FILE):
        descarca_genuri()
    
    with open(GENURI_FILE, 'r') as f:
        lista = json.load(f)
    
    return set(normalizeaza_gen(g) for g in lista)

def filtreaza_genuri(tags_lastfm, genuri_set_norm):
    return [tag for tag in tags_lastfm if normalizeaza_gen(tag) in genuri_set_norm]


FAMILII = {
    'electronic': {'electro', 'synth', 'wave', 'tronica', 'techno', 'house',
                   'trance', 'downtempo', 'ambient', 'glitch', 'idm', 'club',
                   'dance', 'breakcore', 'dnb', 'dubstep'},
    'pop':        {'pop'},
    'rock':       {'rock'},
    'indie':      {'indie'},
    'folk':       {'folk', 'singersongwriter', 'acoustic', 'americana'},
    'hiphop':     {'hiphop', 'rap', 'trap'},
    'rnb_soul':   {'rnb', 'soul', 'funk', 'neosoul'},
    'jazz':       {'jazz'},
    'experimental': {'experimental', 'avantgarde', 'noise'},
}

def familii_gen(gen):
    """Familiile la care aparține un tag, după rădăcini (substring)."""
    rez = set()
    for familie, cuvinte in FAMILII.items():
        if any(c in gen for c in cuvinte):
            rez.add(familie)
    return rez


    
    