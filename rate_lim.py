import time
from collections import defaultdict, deque
from threading import Lock

MAX_CERERI = 10
FEREASTRA_SECUNDE = 60

_istoric = defaultdict(deque)
_lock = Lock()

def permite_cerere(ip):
    now = time.time()
    lim_timp = now - FEREASTRA_SECUNDE

    with _lock:
        timestamps = _istoric[ip]
        while timestamps and timestamps[0] < lim_timp:
            timestamps.popleft()
        if len(timestamps) >= MAX_CERERI:
            return False
        timestamps.append(now)
        return True
    
def curata_ipuri_vechi():
    now = time.time()
    prag = now - FEREASTRA_SECUNDE * 2

    with _lock:
        ipuri_de_sters = []

        for ip, coada in _istoric.items():
            while coada and coada[0] < prag:
                coada.popleft()

            if not coada:
                ipuri_de_sters.append(ip)
        print(f"[CURATARE] Sterg {len(ipuri_de_sters)} IP-URI vechi")
        for ip in ipuri_de_sters:
            del _istoric[ip]
                