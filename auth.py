import requests
import os
import time
from dotenv import load_dotenv

load_dotenv()

_token_cache = {
    'token' : None,
    'expira_la' : 0
}

def get_spotify_token():
    #daca tokenul e valid
    if _token_cache['token'] and time.time() < _token_cache['expira_la'] - 60:
        return _token_cache['token']

    CLIENT_ID = os.getenv("SPOTIFY_ID")
    CLIENT_SECRET = os.getenv("SPOTIFY_SECRET")
    AUTH_URL = 'https://accounts.spotify.com/api/token'

    date_trimise = {'grant_type' : 'client_credentials'}

    raspuns = requests.post(AUTH_URL, data=date_trimise, auth=(CLIENT_ID, CLIENT_SECRET))

    if raspuns.status_code !=200:
        raise Exception(f"Nu am putut obtine tokenul: {raspuns.status_code}")
    
    date_token = raspuns.json()
    token_acces = date_token['access_token']
    durata_valabilitate = date_token['expires_in'] #3600

    _token_cache['token'] = token_acces
    _token_cache['expira_la'] = time.time() + durata_valabilitate

    return token_acces





