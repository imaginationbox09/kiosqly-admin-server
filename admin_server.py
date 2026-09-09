import base64
from functools import wraps
import os
from datetime import datetime, timezone
from flask import Flask, render_template, render_template_string, request, jsonify, redirect, session, url_for
from pymongo import ASCENDING, DESCENDING, MongoClient, ReturnDocument
from werkzeug.security import check_password_hash

import os
app = Flask(__name__, template_folder=os.path.join(os.path.dirname(os.path.abspath(__file__)), "templates"))
app.secret_key = os.getenv('FLASK_SECRET_KEY') or os.urandom(32)
app.config.update(
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE='Lax',
    SESSION_COOKIE_SECURE=os.getenv('SESSION_COOKIE_SECURE', '').lower() == 'true'
)
HEARTBEAT_TIMEOUT_SECONDS = 90
mongo_client = None
ADMIN_USERNAME = os.getenv('ADMIN_USERNAME', 'info@kiosqly.com')
ADMIN_PASSWORD_HASH = os.getenv(
    'ADMIN_PASSWORD_HASH',
    'scrypt:32768:8:1$XnX8CTb5E8EvRrqv$974b4141d062dbf8f8bae741f56f4619200c41f5fd5d7a680baf0c0fc929b2db27e2f02260c7325e1568019fa899b96d5d483380a85d5e6c4ca571395c665eff'
)


def admin_required(view):
    @wraps(view)
    def wrapped_view(*args, **kwargs):
        if session.get('admin_authenticated') is True:
            return view(*args, **kwargs)
        if request.path.startswith('/api/') or request.path == '/send_cmd':
            return jsonify({'success': False, 'message': 'Autenticacion requerida'}), 401
        return redirect(url_for('login', next=request.full_path))
    return wrapped_view


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
    try:
        coll = get_devices_collection()
        raw_devices = list(coll.find({}))
        safe_devices = []
        for d in raw_devices:
            if isinstance(d, dict):
                d["_id"] = str(d.get("_id", ""))
                safe_devices.append(d)
            elif isinstance(d, str):
                safe_devices.append({"device_name": d, "device_id": d})
        return safe_devices
    except Exception as e:
        print("Error obteniendo dispositivos:", e)
        return []

def add_cors_headers(response):
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type'
    response.headers['Access-Control-Allow-Methods'] = 'GET,POST,OPTIONS'
    return response


def device_for_api(device_id, device):
    last_seen = device.get('last_seen')
    if last_seen:
        try:
            last_seen_at = last_seen if isinstance(last_seen, datetime) else datetime.fromisoformat(last_seen)
            if last_seen_at.tzinfo is None:
                last_seen_at = last_seen_at.replace(tzinfo=timezone.utc)
            is_online = (datetime.now(timezone.utc) - last_seen_at).total_seconds() < HEARTBEAT_TIMEOUT_SECONDS
        except (TypeError, ValueError):
            is_online = False
    else:
        is_online = False
    
    # Obtener nombre del negocio
    business_name = device.get('restaurant_id') or device.get('business_name') or device.get('tenant')
    
    return {
        'deviceId': device_id,
        'restaurantId': device.get('restaurant_id', 'Sin asignar'),
        'businessName': business_name,  # ← NUEVO: Campo para agrupación
        'businessId': device.get('business_id'),  # ← NUEVO
        'tenant': business_name,  # ← NUEVO: Alternativa a businessName
        'name': device.get('alias') or device.get('device_name', 'Tableta sin nombre'),
        'alias': device.get('alias', ''),
        'location': device.get('location', 'Ubicacion no registrada'),
        'localIp': device.get('local_ip', 'N/A'),
        'publicIp': device.get('public_ip', 'N/A'),
        'appVersion': device.get('app_version', 'N/D'),
        'batteryLevel': device.get('battery', 0),
        'isCharging': device.get('is_charging', False),
        'wifiSignal': device.get('wifi_signal_strength', 0),
        'wifiSsid': device.get('wifi_ssid', 'N/A'),
        'ramFreeMb': device.get('ram_free_mb', 'N/A'),
        'ramTotalMb': device.get('ram_total_mb', 'N/A'),
        'storageFreeMb': device.get('storage_free_mb', 'N/A'),
        'storageTotalMb': device.get('storage_total_mb', 'N/A'),
        'brightness': device.get('brightness', 'N/A'),
        'volume': device.get('volume', 'N/A'),
        'gps': device.get('gps', 'N/A'),
        'lastPing': last_seen.isoformat() if isinstance(last_seen, datetime) else last_seen,
        'status': 'ONLINE' if is_online else 'OFFLINE',
    }



@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        if username == ADMIN_USERNAME and check_password_hash(ADMIN_PASSWORD_HASH, password):
            session.clear()
            session['admin_authenticated'] = True
            next_url = request.args.get('next') or url_for('home')
            if not next_url.startswith('/') or next_url.startswith('//'):
                next_url = url_for('home')
            return redirect(next_url)
        error = 'Usuario o clave incorrectos.'
    return render_template('login.html', error=error)


@app.route('/logout', methods=['POST'])
@admin_required
def logout():
    session.clear()
    return redirect(url_for('login'))


@app.route('/')
@admin_required
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
        'ram_total_mb': data.get('ram_total_mb', 'N/A'),
        'storage_free_mb': data.get('storage_free_mb', 'N/A'),
        'storage_total_mb': data.get('storage_total_mb', 'N/A'),
        'network_type': data.get('network_type', 'N/A'),
        'wifi_signal_strength': data.get('wifi_signal_strength', 0),
        'wifi_ssid': data.get('wifi_ssid', 'N/A'),
        'brightness': data.get('brightness', 'N/A'),
        'volume': data.get('volume', 'N/A'),
        'gps': data.get('gps', 'N/A'),
        'latitude': data.get('latitude'),
        'longitude': data.get('longitude')
    }
    if data.get('alias') is not None:
        telemetry['alias'] = data['alias']

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
@admin_required
def list_kiosks_api():
    if request.method == 'OPTIONS':
        return '', 204
    devices = [device_for_api(device.get('device_id'), device)
               for device in get_devices_for_dashboard()
               if device.get('device_id')]
    devices.sort(key=lambda device: device.get('lastPing') or '', reverse=True)
    return jsonify({'success': True, 'data': devices}), 200


@app.route('/api/v1/kiosks/<device_id>/command', methods=['POST', 'OPTIONS'])
@admin_required
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
    if data.get('url'):
        command_payload['url'] = data['url']
    if data.get('wallpaper'):
        command_payload['wallpaper'] = data['wallpaper']
    if data.get('alias'):
        command_payload['alias'] = data['alias']
    if data.get('value') is not None:
        command_payload['value'] = data['value']
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
@admin_required
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
        elif command == 'set_wallpaper':
            cmd_payload['url'] = request.form.get('wallpaper_url')

        get_devices_collection().update_one(
            {'device_id': device_id},
            {'$push': {'pending_commands': cmd_payload}}
        )

    return render_template_string('<script>alert("Comando enviado a la tableta."); window.location.href="/";</script>')

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)