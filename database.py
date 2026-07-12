import sqlite3
import json
import time

NUME_BAZA_DATE = 'istoric_spotify.db'

def setup_database():
    conn = sqlite3.connect(NUME_BAZA_DATE)
    cursor = conn.cursor()

    
    
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS Piese (
        spotify_id TEXT PRIMARY KEY,
        nume TEXT NOT NULL,
        artist TEXT NOT NULL,
        album TEXT,
        link_spotify TEXT,
        imagine_url TEXT,
        durata TEXT
    )
    ''')
    
    #tabel cautari
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS Cautari (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        query TEXT NOT NULL UNIQUE,
        timestamp INTEGER NOT NULL,
        rezultate_json TEXT NOT NULL
    )
    ''')

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS LastFmTrackInfo(
        cheie_cautare TEXT PRIMARY KEY,
        data TEXT,
        timestamp INT
    )
    ''')


    cursor.execute('''
    CREATE TABLE IF NOT EXISTS LastFmSimilar(
        cheie_cautare TEXT PRIMARY KEY,
        data TEXT,
        timestamp INT
    )
    ''')

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS LastFmArtistTags(
        artist TEXT PRIMARY KEY,
        data TEXT,
        timestamp INT
    )
    ''')


    cursor.execute('''
    CREATE TABLE IF NOT EXISTS SpotifyImageMap(
        nume_artist TEXT,
        nume_piesa TEXT,
        url TEXT,
        spotify_id TEXT DEFAULT '',
        timestamp INT,
        PRIMARY KEY(nume_artist, nume_piesa)
    )
    ''')


    #pt musicbrainz
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS MusicBrainzRecording(
        mbid TEXT PRIMARY KEY,
        rezultat TEXT,
        data_cautare TIMESTAMP DEFAULT CURRENT_TIMESTAMP  
    )
    ''')

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS MusicBrainzArtist(
        mbid TEXT PRIMARY KEY,
        rezultat TEXT,
        data_cautare TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )   
    ''')

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS HomepageTracks(
        spotify_id TEXT PRIMARY KEY,
        data TEXT,
        timestamp INT
    )
    ''')

    #pentru listenbrainz
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS ListenBrainzSimilarArtists(
        artist_mbid TEXT PRIMARY KEY,
        rezultat TEXT,
        timestamp INT
    )
    ''')
    #index pt a gasi cautarile vechi
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_cautari_query ON Cautari(query)')
    
    conn.commit()
    conn.close()




def normalizeaza_query(query):
    return ' '.join(query.lower().strip().split())


def cauta_in_cache(query, max_varsta_zile=7):
    query_curat = normalizeaza_query(query)
    limita_timp = int(time.time()) - (max_varsta_zile * 24 * 60 * 60)
    
    conn = sqlite3.connect(NUME_BAZA_DATE)
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT rezultate_json, timestamp FROM Cautari 
        WHERE query = ? AND timestamp > ?
    ''', (query_curat, limita_timp))
    
    rand = cursor.fetchone()
    conn.close()
    
    if rand is None:
        return None
    
    
    rezultate = json.loads(rand[0])
    return rezultate


def salveaza_cautare(query, rezultate):
    query_curat = normalizeaza_query(query)
    timestamp_curent = int(time.time())
    rezultate_json = json.dumps(rezultate)
    
    conn = sqlite3.connect(NUME_BAZA_DATE)
    cursor = conn.cursor()
    
   
    cursor.execute('''
        INSERT OR REPLACE INTO Cautari (query, timestamp, rezultate_json)
        VALUES (?, ?, ?)
    ''', (query_curat, timestamp_curent, rezultate_json))
    
    
    for piesa in rezultate:
        cursor.execute('''
            INSERT OR IGNORE INTO Piese 
            (spotify_id, nume, artist, album, link_spotify, imagine_url, durata)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            piesa.get('id'),
            piesa.get('name'),
            piesa.get('artist'),
            piesa.get('album'),
            piesa.get('link'),
            piesa.get('image'),
            piesa.get('duration')
        ))
    
    conn.commit()
    conn.close()


def curata_cautari_vechi(max_varsta_zile=30):
    limita_timp = time.time() - (max_varsta_zile * 24 * 60 * 60)
    
    conn = sqlite3.connect(NUME_BAZA_DATE)
    cursor = conn.cursor()
    cursor.execute('DELETE FROM Cautari WHERE timestamp < ?', (limita_timp,))
    conn.commit()
    conn.close()


def cauta_track_info_in_cache(cheie, max_varsta_zile = 7):
    #verifica daca avem in cache info pt cheia data. returneaza dictionarul sau none

    limita_timp = int(time.time()) - (max_varsta_zile * 24 * 60 * 60)

    conn = sqlite3.connect(NUME_BAZA_DATE)
    cursor = conn.cursor()

    cursor.execute('''
    SELECT data FROM LastFmTrackInfo
    WHERE cheie_cautare = ? AND timestamp > ?
    ''', (cheie, limita_timp))

    rand = cursor.fetchone()
    conn.close()

    if rand is None:
        return None
    
    return json.loads(rand[0])

def salveaza_track_info(cheie, info_dict):
    #salveaza un info dict in cache sau il actualizeaza daca ex
    if info_dict is None:
        return

    timestamp_curent = int(time.time())
    data_json = json.dumps(info_dict)

    conn = sqlite3.connect(NUME_BAZA_DATE)
    cursor = conn.cursor()

    cursor.execute('''
    INSERT OR REPLACE INTO LastFmTrackInfo (cheie_cautare, data, timestamp)
    VALUES(?, ?, ?)
    ''', (cheie, data_json, timestamp_curent))

    conn.commit()
    conn.close()


def cauta_artist_tags_in_cache(artist, max_varsta_zile=30):
    artist_curat = artist.lower().strip()
    limita_timp = int(time.time()) - (max_varsta_zile * 24 * 60 * 60)

    conn = sqlite3.connect(NUME_BAZA_DATE)
    cursor = conn.cursor()

    cursor.execute('''
    SELECT data FROM LastFmArtistTags
    WHERE artist = ? AND timestamp > ?
    ''', (artist_curat, limita_timp))

    rand = cursor.fetchone()
    conn.close()

    if rand is None:
        return None
    return json.loads(rand[0])


def salveaza_artist_tags(artist, tags):
    if tags is None:
        return

    artist_curat = artist.lower().strip()
    timestamp_curent = int(time.time())
    data_json = json.dumps(tags)

    conn = sqlite3.connect(NUME_BAZA_DATE)
    cursor = conn.cursor()

    cursor.execute('''
    INSERT OR REPLACE INTO LastFmArtistTags (artist, data, timestamp)
    VALUES (?, ?, ?)
    ''', (artist_curat, data_json, timestamp_curent))

    conn.commit()
    conn.close()


def cauta_similar_in_cache(cheie, max_varsta_zile = 7):
    #verifica daca avem in cache info pt cheia data. returneaza dictionarul sau none

    limita_timp = int(time.time()) - (max_varsta_zile * 24 * 60 * 60)

    conn = sqlite3.connect(NUME_BAZA_DATE)
    cursor = conn.cursor()

    cursor.execute('''
    SELECT data FROM LastFmSimilar
    WHERE cheie_cautare = ? AND timestamp > ?
    ''', (cheie, limita_timp))

    rand = cursor.fetchone()
    conn.close()

    if rand is None:
        return None
    
    return json.loads(rand[0])


def salveaza_similar(cheie, lista):
    #salveaza un info dict in cache sau il actualizeaza daca ex
    if lista is None:
        return

    timestamp_curent = int(time.time())
    data_json = json.dumps(lista)

    conn = sqlite3.connect(NUME_BAZA_DATE)
    cursor = conn.cursor()

    cursor.execute('''
    INSERT OR REPLACE INTO LastFmSimilar (cheie_cautare, data, timestamp)
    VALUES(?, ?, ?)
    ''', (cheie, data_json, timestamp_curent))

    conn.commit()
    conn.close()


def cauta_imagine_spotify(nume_artist, nume_piesa, max_varsta_zile=30):
    artist_curat = nume_artist.lower().strip()
    piesa_curata = nume_piesa.lower().strip()

    limita_timp = int(time.time()) - (max_varsta_zile * 24 * 60 * 60)

    conn = sqlite3.connect(NUME_BAZA_DATE)
    cursor = conn.cursor()

    cursor.execute('''
    SELECT url, spotify_id FROM SpotifyImageMap
    WHERE nume_artist = ? AND nume_piesa = ? AND timestamp > ?
    ''', (artist_curat, piesa_curata, limita_timp))

    rand = cursor.fetchone()
    conn.close()

    if rand is None:
        return None
    return {'url': rand[0], 'spotify_id': rand[1] or ''}


def salveaza_imagine_spotify(nume_artist, nume_piesa, url, spotify_id=''):
    if not url:
        return
    
    artist_curat = nume_artist.lower().strip()
    piesa_curata = nume_piesa.lower().strip()
    timestamp_curent = int(time.time())

    conn = sqlite3.connect(NUME_BAZA_DATE)
    cursor = conn.cursor()

    cursor.execute('''
    INSERT OR REPLACE INTO SpotifyImageMap (nume_artist, nume_piesa, url, spotify_id, timestamp)
    VALUES (?, ?, ?, ?, ?)
    ''', (artist_curat, piesa_curata, url, spotify_id, timestamp_curent))

    conn.commit()
    conn.close()




#FUNCTII CACHE PT MUSICBRAINZ - recording

def cauta_recording_in_cache(mbid, max_varsta_zile=30):
    limita_timp = int(time.time()) - (max_varsta_zile * 24 * 60 * 60)

    conn = sqlite3.connect(NUME_BAZA_DATE)
    cursor = conn.cursor()

    cursor.execute('''
        SELECT rezultat FROM MusicBrainzRecording
        WHERE mbid = ? AND data_cautare > ?
    ''', (mbid, limita_timp))

    rand = cursor.fetchone()
    conn.close()

    if rand is None:
        return None
    return json.loads(rand[0])

def salveaza_recording_in_cache(mbid, info_dict):
    if info_dict is None:
        return 
    timestamp_curent = int(time.time())
    data_json = json.dumps(info_dict)

    conn = sqlite3.connect(NUME_BAZA_DATE)
    cursor = conn.cursor()

    cursor.execute('''
    INSERT OR REPLACE INTO MusicBrainzRecording (mbid, rezultat, data_cautare)
    VALUES(?, ?, ?)
    ''', (mbid, data_json, timestamp_curent))

    conn.commit()
    conn.close()


#FUNCTII CACHE PENTRU MUSICBRAINZ - artist

def cauta_artist_mb_in_cache(mbid, max_varsta_zile=30):
    limita_timp = int(time.time()) - (max_varsta_zile * 24 * 60 * 60)

    conn = sqlite3.connect(NUME_BAZA_DATE)
    cursor = conn.cursor()

    cursor.execute('''
        SELECT rezultat FROM MusicBrainzArtist
        WHERE mbid = ? AND data_cautare > ?
    ''', (mbid, limita_timp))

    rand = cursor.fetchone()
    conn.close()

    if rand is None:
        return None
    return json.loads(rand[0])

def salveaza_artist_mb(mbid, info_dict):
    if info_dict is None:
        return 
    timestamp_curent = int(time.time())
    data_json = json.dumps(info_dict)

    conn = sqlite3.connect(NUME_BAZA_DATE)
    cursor = conn.cursor()

    cursor.execute('''
    INSERT OR REPLACE INTO MusicBrainzArtist (mbid, rezultat, data_cautare)
    VALUES(?, ?, ?)
    ''', (mbid, data_json, timestamp_curent))

    conn.commit()
    conn.close()



def cauta_lb_similar_in_cache(artist_mbid, max_varsta_zile=30):
    limita_timp = int(time.time()) - (max_varsta_zile * 24 * 60 * 60)

    conn = sqlite3.connect(NUME_BAZA_DATE)
    cursor = conn.cursor()

    cursor.execute('''
    SELECT rezultat FROM ListenBrainzSimilarArtists
    WHERE artist_mbid = ? AND timestamp > ?
    ''', (artist_mbid, limita_timp))

    rand = cursor.fetchone()
    conn.close()

    if rand is None:
        return None
    return json.loads(rand[0])


def salveaza_lb_similar(artist_mbid, lista):
    if lista is None:
        return
    
    timestamp_curent = int(time.time())
    data_json = json.dumps(lista)

    conn = sqlite3.connect(NUME_BAZA_DATE)
    cursor = conn.cursor()

    cursor.execute('''
    INSERT OR REPLACE INTO ListenBrainzSimilarArtists (artist_mbid, rezultat, timestamp)
    VALUES (?, ?, ?)
    ''', (artist_mbid, data_json, timestamp_curent))

    conn.commit()
    conn.close()

def cauta_homepage_track_in_cache(spotify_id, max_varsta_zile=30):
    limita_timp = int(time.time()) - (max_varsta_zile * 24 * 60 * 60)
    conn = sqlite3.connect(NUME_BAZA_DATE)
    cursor = conn.cursor()
    cursor.execute('''
        SELECT data FROM HomepageTracks
        WHERE spotify_id = ? AND timestamp > ?
    ''', (spotify_id, limita_timp))
    rand = cursor.fetchone()
    conn.close()
    if rand is None:
        return None
    return json.loads(rand[0])


def salveaza_homepage_track(spotify_id, info_dict):
    if info_dict is None:
        return
    timestamp_curent = int(time.time())
    data_json = json.dumps(info_dict)
    conn = sqlite3.connect(NUME_BAZA_DATE)
    cursor = conn.cursor()
    cursor.execute('''
    INSERT OR REPLACE INTO HomepageTracks (spotify_id, data, timestamp)
    VALUES (?, ?, ?)
    ''', (spotify_id, data_json, timestamp_curent))
    conn.commit()
    conn.close()

