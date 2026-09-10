import os
from flask import Flask, jsonify, request, render_template
from pymongo import MongoClient

# Configuramos Flask para que busque las plantillas en la raíz del proyecto (o donde tengas tu index.html)
app = Flask(__name__, template_folder="../", static_folder="../static")

# Conexión a MongoDB usando la variable de entorno de Vercel
MONGO_URI = os.environ.get("MONGODB_URI")

if not MONGO_URI:
    raise ValueError("No se encontró la variable de entorno MONGODB_URI")

client = MongoClient(MONGO_URI)
db = client["kiosqly_db"]

@app.route("/", methods=["GET"])
def home():
    # Renderiza directamente tu index.html en lugar de devolver texto JSON
    return render_template("index.html")

@app.route("/api/devices", methods=["GET"])
def get_devices():
    try:
        devices_collection = db.devices
        devices = list(devices_collection.find({}, {"_id": 0}))
        return jsonify({"success": True, "devices": devices})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/api/heartbeat", methods=["POST"])
def heartbeat():
    data = request.get_json()
    if not data:
        return jsonify({"success": False, "error": "No JSON provided"}), 400
    
    return jsonify({"success": True, "message": "Heartbeat received"})

if __name__ == "__main__":
    app.run(debug=True)