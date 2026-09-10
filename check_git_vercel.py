import subprocess
import urllib.request
import urllib.error
import json

print("--- ESTADO DE GIT ---")
try:
    status_output = subprocess.check_output(["git", "status"], text=True)
    print(status_output)
    
    log_output = subprocess.check_output(["git", "log", "-n", "3", "--oneline"], text=True)
    print("Últimos commits:")
    print(log_output)
except Exception as e:
    print(f"Error al verificar Git: {e}")

print("--- DIAGNÓSTICO EN VIVO (VERCEL) ---")
base_url = "https://kiosqly-admin-server-global.vercel.app"
for route in ["/", "/devices", "/heartbeat"]:
    url = base_url + route
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req) as response:
            print(f"GET {route} -> Status: {response.status}")
    except urllib.error.HTTPError as e:
        print(f"GET {route} -> HTTPError: {e.code} ({e.reason})")
    except Exception as e:
        print(f"GET {route} -> Error: {e}")
