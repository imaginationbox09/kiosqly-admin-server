import os
from flask import Flask, jsonify, request
from pymongo import MongoClient

app = Flask(__name__)

MONGO_URI = os.environ.get("MONGODB_URI")

if not MONGO_URI:
    raise ValueError("No se encontró la variable de entorno MONGODB_URI")

client = MongoClient(MONGO_URI)
db = client["kiosqly_db"]

@app.route("/", methods=["GET"])
def home():
    # Lee index.html directamente desde la carpeta api/
    base_dir = os.path.dirname(os.path.abspath(__file__))
    html_path = os.path.join(base_dir, "index.html")
        
    try:
        with open(html_path, "r", encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        return f"No se pudo cargar el dashboard: {str(e)}", 500

@app.route("/devices", methods=["GET"])
def get_devices():
    try:
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
    
    return jsonify({"success": True, "message": "Heartbeat received"})

if __name__ == "__main__":
    app.run(debug=True)