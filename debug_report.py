import urllib.request
import urllib.error

base_url = "https://kiosqly-admin-server-global.vercel.app"

print("--- DIAGNÓSTICO EN VIVO (VERCEL) ---")
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
