from flask import Flask, render_template, request, redirect, url_for, session
from pymongo import MongoClient
from bson.objectid import ObjectId
from collections import defaultdict
import os

# Configuración de Flask y MongoDB Atlas
app = Flask(__name__)
app.secret_key = "kiosqly_secret_key"

MONGO_URI = os.getenv("MONGO_URI", "mongodb+srv://kiosqly_db_user:Panama2022@kiosqly.5nkuk2g.mongodb.net/?retryWrites=true&w=majority&appName=kiosqly")
client = MongoClient(MONGO_URI)
db = client['kiosqly']

@app.route('/')
def index():
    # Obtener dispositivos de la base de datos
    devices = list(db.devices.find())
    
    # Agrupar dispositivos por businessName para la vista de Jinja
    grouped_devices = defaultdict(list)
    for dev in devices:
        b_name = dev.get('businessName', 'Sin Asignar')
        grouped_devices[b_name].append(dev)
        
    return render_template('index.html', grouped_devices=dict(grouped_devices))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
