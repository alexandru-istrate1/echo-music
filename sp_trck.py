import requests
import unicodedata
import re
import time
from database import cauta_imagine_spotify, salveaza_imagine_spotify
from concurrent.futures import ThreadPoolExecutor


def formateaza_durata(ms):
    secunde = int((ms / 1000) % 60)
    minute = int((ms / (1000 * 60)) % 60)
    return f"{minute}:{secunde:02d}"


def curata_text(text):
    if not text:
        return ""
    text_fara_accente = ''.join(
        c for c in unicodedata.normalize('NFD', text) 
        if unicodedata.category(c) != 'Mn'
    )
    text_fara_simboluri = re.sub(r'[^\w\s]', ' ', text_fara_accente)
    return ' '.join(text_fara_simboluri.lower().split())



def contine_ca_cuvant(text, cuvant):
    # \b = word boundary. re.escape scapa caractere speciale daca are
    pattern = r'\b' + re.escape(cuvant) + r'\b'
    return bool(re.search(pattern, text))


def normalizeaza_titlu_pentru_dedup(titlu):

    titlu_curat = titlu.lower()
    
    # scoate tot ce e intre paranteze
    titlu_curat = re.sub(r'\([^)]*\)', '', titlu_curat)
    titlu_curat = re.sub(r'\[[^\]]*\]', '', titlu_curat)
    
    # scoate remastered etc
    cuvinte_de_sters = [
        'remaster', 'remastered', 'deluxe', 'expanded', 'bonus',
        'radio edit', 'radio version', 'extended', 'extended version',
        'single version', 'album version', 'demo', 'alternate'
    ]
    for cuvant in cuvinte_de_sters:
        pattern = r'\s*[-–]\s*\d*\s*' + cuvant + r'.*$'
        titlu_curat = re.sub(pattern, '', titlu_curat)
    
    return curata_text(titlu_curat)


def calculeaza_scor_relevanta(piesa, cuvinte_cautate, query_complet):
    nume = curata_text(piesa.get('name', ''))
    artist = curata_text(piesa.get('artist', ''))
    album = curata_text(piesa.get('album', ''))
    popularitate = piesa.get('popularitate_spotify', 0)
    
    # Treapta 1: Titlu exact = query
    if nume == query_complet:
        return 10000 + popularitate
    
    # Treapta 2: Titlul incepe cu query (ca fraza)
    if nume.startswith(query_complet + ' '):
        return 5000 + popularitate
    
    # Treapta 3: Titlul contine query ca fraza intreaga
    if contine_ca_cuvant(nume, query_complet):
        return 2000 + popularitate
    
    # Treapta 4: Artistul contine query ca fraza intreaga
    if contine_ca_cuvant(artist, query_complet):
        return 1000 + popularitate
    
    # Treapta 5: Toate cuvintele din query apar ca cuvinte intregi in titlu
    if all(contine_ca_cuvant(nume, cuv) for cuv in cuvinte_cautate):
        return 500 + popularitate
    
    # Treapta 6: Macar ceva se potriveste (cuvinte intregi)
    text_combinat = f"{nume} {artist} {album}"
    cuvinte_gasite = sum(
        1 for cuv in cuvinte_cautate 
        if contine_ca_cuvant(text_combinat, cuv)
    )
    if cuvinte_gasite > 0:
        return 100 + cuvinte_gasite * 10 + popularitate * 0.1
    
   
    return popularitate #scor 0 - 100 daca nu mai sunt

def search_track(nume_piesa, token_acces):
    
    SEARCH_URL = 'https://api.spotify.com/v1/search'
    headere = {'Authorization': f'Bearer {token_acces}'}
    
    NUMAR_TINTA = 15
    piese_dupa_amprenta = {}  # amprenta (nume+artist) -> piesa
    offset = 0
    MAX_PAGINI = 2
    
    for pagina in range(MAX_PAGINI):
        parametri = {
            'q': nume_piesa,
            'type': 'track',
            'market': 'US',
            'offset': str(offset)
        }
        
        try:
            raspuns = requests.get(SEARCH_URL, headers=headere, params=parametri, timeout=5)
        except requests.exceptions.Timeout:
            print("Spotify a durat prea mult")
            break
        
        if raspuns.status_code == 429:
            timp_asteptare = int(raspuns.headers.get('Retry-After', 3))
            if timp_asteptare > 5:
                break
            time.sleep(timp_asteptare)
            continue
        
        if raspuns.status_code != 200:
            print(f"Eroare Spotify: {raspuns.status_code}")
            break
        
        piese_brute = raspuns.json().get('tracks', {}).get('items', [])
        if not piese_brute:
            break
        
        for piesa_bruta in piese_brute:
            id_piesa = piesa_bruta.get('id', '')
            if not id_piesa:
                continue
            
            lista_artisti = piesa_bruta.get('artists', [])
            artist_principal = lista_artisti[0].get('name', 'Unknown') if lista_artisti else 'Unknown'
            nume_piesa_bruta = piesa_bruta.get('name', 'Unknown')
            
            # Amprenta unica: nume + artist 
            amprenta = f"{normalizeaza_titlu_pentru_dedup(nume_piesa_bruta)}|{curata_text(artist_principal)}"
            popularitate_curenta = piesa_bruta.get('popularity', 0)
            
            # daca avem deja, pastram pe cea mai populara
            if amprenta in piese_dupa_amprenta:
                if popularitate_curenta <= piese_dupa_amprenta[amprenta].get('popularitate_spotify', 0):
                    continue
            
            imagini = piesa_bruta.get('album', {}).get('images', [])
            if len(imagini) >= 3:
                poza = imagini[2].get('url', '')
            elif imagini:
                poza = imagini[-1].get('url', '')
            else:
                poza = ''
            
            piese_dupa_amprenta[amprenta] = {
                'id': id_piesa,
                'name': nume_piesa_bruta,
                'artist': artist_principal,
                'album': piesa_bruta.get('album', {}).get('name', 'Unknown'),
                'link': piesa_bruta.get('external_urls', {}).get('spotify', '#'),
                'image': poza,
                'duration': formateaza_durata(piesa_bruta.get('duration_ms', 0)),
                'popularitate_spotify': popularitate_curenta
            }
        
        if len(piese_dupa_amprenta) >= NUMAR_TINTA:
            break
        
        offset += 20
    
    piese_procesate = list(piese_dupa_amprenta.values())
    
    if not piese_procesate:
        return []
    
    query_curat = curata_text(nume_piesa)
    cuvinte = query_curat.split()
    
    piese_procesate.sort(
        key=lambda p: calculeaza_scor_relevanta(p, cuvinte, query_curat),
        reverse=True
    )
    
    for piesa in piese_procesate:
        piesa.pop('popularitate_spotify', None)
    
    return piese_procesate[:NUMAR_TINTA]

def get_track_by_id(track_id, token_acces):
    
    TRACK_URL = f'https://api.spotify.com/v1/tracks/{track_id}'
    headere = {'Authorization': f'Bearer {token_acces}'}
    
    raspuns = requests.get(TRACK_URL, headers=headere, timeout=10)
    
    if raspuns.status_code != 200:
        return None
    
    piesa = raspuns.json()
    lista_artisti = piesa.get('artists', [])
    imagini = piesa.get('album', {}).get('images', [])
    
    return {
        'id': track_id,
        'name': piesa.get('name', 'Unknown'),
        'artist': lista_artisti[0].get('name', 'Unknown') if lista_artisti else 'Unknown',
        'album': piesa.get('album', {}).get('name', 'Unknown'),
        'link': piesa.get('external_urls', {}).get('spotify', '#'),
        'image': imagini[0].get('url', '') if imagini else '',
        'duration': formateaza_durata(piesa.get('duration_ms', 0))
    }


def enrich_spotify_images(piese, token_acces):
    SEARCH_URL = 'https://api.spotify.com/v1/search'
    headere = {'Authorization': f'Bearer {token_acces}'}
    
    def proceseaza_o_piesa(piesa):
        cached = cauta_imagine_spotify(piesa['artist'], piesa['name'], max_varsta_zile=30)
        if cached is not None:
            piesa['image'] = cached['url']
            piesa['spotify_id'] = cached['spotify_id']
            return piesa

        try : 
            parametri = {
                'q' : f"track:{piesa['name']} artist:{piesa['artist']}",
                'type' : 'track',
                'limit' : '1'
            }
            raspuns = requests.get(SEARCH_URL, headers=headere, params=parametri, timeout=7)

            if raspuns.status_code != 200:
                return piesa

            items = raspuns.json().get('tracks', {}).get('items', [])
            if not items:
                return piesa

            primul = items[0]

            nume_gasit = primul.get('name', '').lower().strip()
            artist_gasit = ''
            artisti = primul.get('artists', [])
            if artisti:
                artist_gasit = artisti[0].get('name', '').lower().strip()
            nume_cautat = piesa['name'].lower().strip()
            artist_cautat = piesa['artist'].lower().strip()
            if nume_gasit == nume_cautat and artist_gasit == artist_cautat:    
                piesa['spotify_id'] = primul.get('id', '')
                
                imagini = primul.get('album', {}).get('images', [])
                if imagini:
                    if len(imagini) >= 3:
                        url_nou = imagini[2].get('url', piesa['image'])
                    else:
                        url_nou = imagini[-1].get('url', piesa['image'])
                    if url_nou:
                        piesa['image'] = url_nou
                        salveaza_imagine_spotify(piesa['artist'], piesa['name'], url_nou, piesa.get('spotify_id', ''))
                    
        except Exception as e:
            print(f"Eroare pentru piesa {piesa['name']} : {e}")
        
        return piesa
    
    with ThreadPoolExecutor(max_workers=3) as executor:
        piese = list(executor.map(proceseaza_o_piesa, piese))
    
    return piese