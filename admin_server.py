import base64
import os
from datetime import datetime, timezone
from flask import Flask, render_template, request, jsonify
from pymongo import ASCENDING, DESCENDING, MongoClient, ReturnDocument

app = Flask(__name__)
HEARTBEAT_TIMEOUT_SECONDS = 90
mongo_client = None


def get_devices_collection():
    global mongo_client

    mongo_uri = os.getenv('MONGODB_URI') or os.getenv('MONGO_URI')
    if not mongo_uri:
        raise RuntimeError('Falta configurar MONGODB_URI o MONGO_URI')

    if mongo_client is None:
        mongo_client = MongoClient(mongo_uri, serverSelectionTimeoutMS=5000)
        mongo_client.admin.command('ping')

    database_name = os.getenv('MONGODB_DB', 'kiosqly')
    collection = mongo_client[database_name]['devices']
    collection.create_index([('device_id', ASCENDING)], unique=True)
    collection.create_index([('last_seen', DESCENDING)])
    return collection


def get_devices_for_dashboard():
    now = datetime.now(timezone.utc)
    devices = {}
    for device in get_devices_collection().find().sort('last_seen', DESCENDING):
        device_id = device.pop('device_id', str(device.pop('_id', 'sin-id')))
        last_seen = device.get('last_seen')
        if isinstance(last_seen, datetime):
            if last_seen.tzinfo is None:
                last_seen = last_seen.replace(tzinfo=timezone.utc)
            device['last_seen'] = last_seen.isoformat()
            device['status'] = 'ONLINE' if (now - last_seen).total_seconds() < HEARTBEAT_TIMEOUT_SECONDS else 'OFFLINE'
        else:
            device['status'] = 'OFFLINE'
        devices[device_id] = device
    return devices


@app.after_request
def add_cors_headers(response):
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type'
    response.headers['Access-Control-Allow-Methods'] = 'GET,POST,OPTIONS'
    return response


def device_for_api(device_id, device):
    last_seen = device.get('last_seen')
    if last_seen:
        try:
            last_seen_at = datetime.fromisoformat(last_seen)
            is_online = (datetime.now(timezone.utc) - last_seen_at).total_seconds() < HEARTBEAT_TIMEOUT_SECONDS
        except ValueError:
            is_online = False
    else:
        is_online = False
    return {
        'deviceId': device_id,
        'restaurantId': device.get('restaurant_id', 'Sin asignar'),
        'name': device.get('device_name', 'Tableta sin nombre'),
        'location': device.get('location', 'Ubicacion no registrada'),
        'localIp': device.get('local_ip', 'N/A'),
        'publicIp': device.get('public_ip', 'N/A'),
        'appVersion': device.get('app_version', 'N/D'),
        'battery': device.get('battery', 0),
        'is_charging': device.get('is_charging', False),
        'wifiSignalStrength': device.get('wifi_signal_strength', 0),
        'lastPing': last_seen,
        'status': 'ONLINE' if is_online else 'OFFLINE',
    }



@app.route('/')
def home():
    return render_template("index.html", devices=get_devices_for_dashboard())

@app.route('/heartbeat', methods=['POST'])
def heartbeat():
    data = request.get_json(silent=True) or {}
    device_id = data.get("device_id")

    if not device_id:
        return jsonify({'status': 'error', 'message': 'device_id missing'}), 400

    public_ip = request.headers.get('X-Forwarded-For', request.remote_addr)
    if public_ip and ',' in public_ip:
        public_ip = public_ip.split(',')[0].strip()

    # Actualizar telemetría completa
    now = datetime.now(timezone.utc)
    telemetry = {
        'last_seen': now,
        'device_name': data.get('device_name', 'Tableta Desconocida'),
        'restaurant_id': data.get('restaurant_id', data.get('restaurantId', 'Sin asignar')),
        'location': data.get('location', data.get('site_address', 'Ubicacion no registrada')),
        'app_version': data.get('app_version', '1.0.0'),
        'battery': data.get('battery', 0),
        'is_charging': data.get('is_charging', False),
        'current_url': data.get('current_url', 'N/A'),
        'local_ip': data.get('local_ip', 'N/A'),
        'public_ip': public_ip,
        'ram_free_mb': data.get('ram_free_mb', 'N/A'),
        'storage_free_mb': data.get('storage_free_mb', 'N/A'),
        'network_type': data.get('network_type', 'N/A'),
        'wifi_signal_strength': data.get('wifi_signal_strength', 0),
        'latitude': data.get('latitude'),
        'longitude': data.get('longitude')
    }

    previous_device = get_devices_collection().find_one_and_update(
        {'device_id': device_id},
        {'$set': {**telemetry, 'pending_commands': []}, '$setOnInsert': {'device_id': device_id}},
        upsert=True,
        return_document=ReturnDocument.BEFORE
    )

    # Preparar respuesta con comandos pendientes para la tableta
    response_data = {'status': 'ok', 'commands': (previous_device or {}).get('pending_commands', [])}

    return jsonify(response_data), 200


@app.route('/api/v1/kiosks', methods=['GET', 'OPTIONS'])
def list_kiosks_api():
    if request.method == 'OPTIONS':
        return '', 204
    devices = [device_for_api(device_id, device) for device_id, device in get_devices_for_dashboard().items()]
    devices.sort(key=lambda device: device.get('lastPing') or '', reverse=True)
    return jsonify({'success': True, 'data': devices}), 200


@app.route('/api/v1/kiosks/<device_id>/command', methods=['POST', 'OPTIONS'])
def send_command_api(device_id):
    if request.method == 'OPTIONS':
        return '', 204
    data = request.get_json(silent=True) or {}
    command = data.get('command')
    if not command:
        return jsonify({'success': False, 'message': 'command es requerido'}), 400
    collection = get_devices_collection()
    if not collection.find_one({'device_id': device_id}):
        return jsonify({'success': False, 'message': 'Dispositivo no encontrado'}), 404

    command_payload = {'type': command}
    if data.get('message'):
        command_payload['message'] = data['message']
    collection.update_one({'device_id': device_id}, {'$push': {'pending_commands': command_payload}})
    return jsonify({'success': True, 'message': f'Comando {command} encolado'}), 200

@app.route('/upload_image', methods=['POST'])
def upload_image():
    data = request.get_json(silent=True) or {}
    device_id = data.get('device_id')
    image_data = data.get('image_data')

    updated = get_devices_collection().update_one(
        {'device_id': device_id},
        {'$set': {'last_image': image_data}}
    ) if image_data else None
    if updated and updated.matched_count:
        return jsonify({'status': 'photo_received'}), 200

    return jsonify({'status': 'no_image_or_device'}), 400

@app.route('/send_cmd', methods=['POST'])
def send_cmd():
    device_id = request.form.get('device_id')
    command = request.form.get('command')

    if device_id and command:
        cmd_payload = {'type': command}

        if command == 'set_url':
            cmd_payload['url'] = request.form.get('target_url')
        elif command == 'change_wifi':
            cmd_payload['ssid'] = request.form.get('wifi_ssid')
            cmd_payload['password'] = request.form.get('wifi_pass')
        elif command == 'set_brightness':
            cmd_payload['value'] = int(request.form.get('brightness', 128))
        elif command == 'set_volume':
            cmd_payload['value'] = int(request.form.get('volume', 50))

        get_devices_collection().update_one(
            {'device_id': device_id},
            {'$push': {'pending_commands': cmd_payload}}
        )

    return render_template_string('<script>alert("Comando enviado a la tableta."); window.location.href="/";</script>')

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)