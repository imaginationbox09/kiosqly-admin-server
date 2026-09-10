import os
from flask import Flask, jsonify, request
from pymongo import MongoClient

app = Flask(__name__)

# Configuración de MongoDB usando la variable de entorno correcta de Vercel
MONGO_URI = os.environ.get("MONGODB_URI")

if not MONGO_URI:
    raise ValueError("No se encontró la variable de entorno MONGODB_URI")

client = MongoClient(MONGO_URI)
db = client.get_database() # O usa el nombre de tu base de datos, ej: client["tu_base_de_datos"]

@app.route("/", methods=["GET"])
def home():
    return jsonify({"status": "Server is running", "message": "Kiosqly Admin API"})

@app.route("/devices", methods=["GET"])
def get_devices():
    try:
        # Ejemplo de consulta a tu colección de dispositivos
        devices_collection = db.devices
        devices = list(devices_collection.find({}, {"_id": 0}))
        return jsonify({"success": True, "devices": devices})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/heartbeat", methods=["POST"])
def heartbeat():
    data = request.get_json()
    if not data:
        return jsonify({"success": False, "error": "No JSON provided"}), 400
    
    # Lógica de tu heartbeat aquí
    return jsonify({"success": True, "message": "Heartbeat received"})

if __name__ == "__main__":
    app.run(debug=True)