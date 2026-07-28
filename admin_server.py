from flask import Flask, request, jsonify
import json
import os
import base64
from datetime import datetime

app = Flask(__name__)

# Base de datos en memoria
devices = {}
# Bandera para capturar foto en el próximo heartbeat
pending_photos = set()

@app.route('/heartbeat', methods=['POST'])
def heartbeat():
    data = request.json
    device_id = data.get('device_id')

    # Guardar estado del dispositivo
    devices[device_id] = {
        'last_seen': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        'status': data
    }

    print(f"[*] Heartbeat de {device_id}: GPS={data.get('gps')}, Batería={data.get('battery')}%")

    # Verificar si hay una petición de foto para este dispositivo
    should_capture = device_id in pending_photos
    if should_capture:
        pending_photos.remove(device_id)
        print(f"[!] Enviando comando de captura a {device_id}")

    response = {
        "url": "",
        "capture_image": should_capture
    }

    return jsonify(response)

@app.route('/trigger_photo', methods=['GET'])
def trigger_photo():
    # Activa la captura para todos los dispositivos conocidos en su próximo heartbeat
    for dev_id in devices.keys():
        pending_photos.add(dev_id)
    return "Comando de captura enviado. Las tablets tomarán la foto en su próximo reporte (máx 1 min)."

@app.route('/upload_image', methods=['POST'])
def upload_image():
    data = request.json
    device_id = data.get('device_id')
    image_data = data.get('image_data')

    if image_data:
        filename = f"snap_{device_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
        with open(filename, "wb") as f:
            f.write(base64.b64decode(image_data))
        print(f"[SUCCESS] Imagen guardada: {os.path.abspath(filename)}")

    return jsonify({"status": "ok"})

@app.route('/devices', methods=['GET'])
def list_devices():
    return jsonify(devices)

if __name__ == '__main__':
    print("--- Servidor de Administración Kiosqly ---")
    print("1. Asegúrate de que esta PC tenga la IP 192.168.0.7")
    print("2. Abre http://192.168.0.7:5000/trigger_photo para tomar una foto")
    print("------------------------------------------")
    app.run(host='0.0.0.0', port=5000)
