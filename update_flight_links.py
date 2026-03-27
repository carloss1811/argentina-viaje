#!/usr/bin/env python3
"""
Actualiza automáticamente los enlaces de FlightRadar24 en index.html
cuando los vuelos están en el aire. Corre cada 15 min via cron.
"""
import urllib.request, json, re, subprocess, time

REPO = "/home/bitash/projects/argentina-viaje"
HTML = f"{REPO}/index.html"

FLIGHTS = [
    {"num": "AR1133",  "callsign": "ARG1133", "dep": 1774634700, "arr": 1774681800},
    {"num": "IB0105",  "callsign": "IBE0105", "dep": 1774683900, "arr": 1774729500},
]

def get_live_fr24_url(callsign):
    """Busca el vuelo activo via FR24 search API y devuelve la URL o None."""
    url = f"https://www.flightradar24.com/v1/search/web/find?query={callsign}&limit=5"
    req = urllib.request.Request(url, headers={
        "User-Agent": "Mozilla/5.0",
        "Accept": "application/json",
        "Referer": "https://www.flightradar24.com/"
    })
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            data = json.loads(r.read())
        for result in data.get("results", []):
            if result.get("type") == "live":
                fid = result.get("id")
                if fid:
                    return f"https://www.flightradar24.com/{callsign}/{fid}"
        return None
    except Exception as e:
        print(f"Error consultando FR24 para {callsign}: {e}")
        return None

def update_html(flight_num, callsign, new_url):
    with open(HTML, "r") as f:
        content = f.read()
    # Buscar el bloque del vuelo por número y reemplazar data-fr24
    pattern = rf'(<!-- Vuelo \d+: {flight_num}[^\n]*\n.*?data-fr24=")[^"]*(")'
    new_content = re.sub(pattern, lambda m: m.group(1) + new_url + m.group(2), content, flags=re.DOTALL)
    if new_content == content:
        print(f"No encontré el tracker para {flight_num}")
        return False
    with open(HTML, "w") as f:
        f.write(new_content)
    print(f"Actualizado {flight_num}: {new_url}")
    return True

def git_push(message):
    subprocess.run(["git", "-C", REPO, "add", "index.html"], check=True)
    result = subprocess.run(["git", "-C", REPO, "diff", "--cached", "--quiet"])
    if result.returncode != 0:
        subprocess.run(["git", "-C", REPO, "commit", "-m", message], check=True)
        subprocess.run(["git", "-C", REPO, "push", "origin", "main"], check=True)
        print("Push OK")
    else:
        print("Sin cambios")

now = int(time.time())
changed = False

for fl in FLIGHTS:
    if not (fl["dep"] - 1800 <= now <= fl["arr"] + 7200):
        print(f"{fl['num']}: fuera de ventana, skip")
        continue
    print(f"{fl['num']}: en ventana, consultando FR24...")
    url = get_live_fr24_url(fl["callsign"])
    if url:
        if update_html(fl["num"], fl["callsign"], url):
            changed = True
    else:
        print(f"{fl['num']}: no activo todavía")

if changed:
    git_push("Auto: actualizar enlaces FlightRadar24 con ID de vuelo en vivo")
