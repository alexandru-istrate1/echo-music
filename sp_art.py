import requests

def search_artist(nume_artist, token_acces):
    SEARCH_URL = 'https://api.spotify.com/v1/search' #adresa pt functia de search

    headere = { 
        'Authorization': f'Bearer {token_acces}' 
    }

    parametri_cautare = {
        'q' : nume_artist,
        'type' : 'artist',
        'limit' : 1 
    }

    raspuns_cautare  = requests.get(SEARCH_URL, headers=headere, params=parametri_cautare)
    print(f"Status cautare: {raspuns_cautare.status_code}")
    date_artist = raspuns_cautare.json()
    
    return date_artist