import os
import json

print("--- ARCHIVOS EN EL DIRECTORIO ACTUAL ---")
print(os.listdir("."))

if os.path.exists("vercel.json"):
    print("\n--- CONTENIDO DE vercel.json ---")
    with open("vercel.json", "r") as f:
        print(f.read())
else:
    print("\nNo existe vercel.json. Creando uno estándar para Flask...")
    config = {
        "version": 2,
        "builds": [
            {
                "src": "app.py",
                "use": "@vercel/python"
            }
        ],
        "routes": [
            {
                "src": "/(.*)",
                "dest": "app.py"
            }
        ]
    }
    with open("vercel.json", "w") as f:
        json.dump(config, f, indent=2)
    print("vercel.json creado exitosamente.")

