"""Kiosqly fleet API.

`devices` document contract (key fields):
{
  device_id, alias, business_name, location, last_seen, app_version,
  network: {public_ip, local_ip, type, wifi_ssid, signal_dbm},
  location_geo: {latitude, longitude, accuracy_m, updated_at},
  webview_url, lock_state, pending_commands: [{id, type, payload, created_at}],
  media: {screenshot: {url, captured_at}, camera_snapshot: {url, captured_at}}
}
Devices POST telemetry to /heartbeat, poll the returned commands, execute them,
and POST the resulting public media URL to /api/v1/devices/<id>/media.
"""
import base64
import binascii
import hmac
import os
from datetime import datetime, timezone
from functools import wraps
from uuid import uuid4

from flask import Flask, jsonify, redirect, render_template, request, session, url_for
from pymongo import ASCENDING, DESCENDING, MongoClient, ReturnDocument

app = Flask(__name__, template_folder=os.path.join(os.path.dirname(os.path.abspath(__file__)), "templates"))
app.secret_key = os.environ['FLASK_SECRET_KEY']
app.config.update(SESSION_COOKIE_HTTPONLY=True, SESSION_COOKIE_SAMESITE='Lax', SESSION_COOKIE_SECURE=os.getenv('SESSION_COOKIE_SECURE', '').lower() == 'true')
ADMIN_USERNAME = os.getenv('ADMIN_USERNAME', 'info@kiosqly.com')
ADMIN_PASSWORD = os.environ['ADMIN_PASSWORD']
HEARTBEAT_TIMEOUT_SECONDS = 90
COMMAND_TYPES = {'set_url', 'update_app', 'lock_device', 'unlock_device', 'take_screenshot', 'take_photo'}
MEDIA_TYPES = {'screenshot', 'camera_snapshot'}
MAX_MEDIA_BYTES = 5 * 1024 * 1024
mongo_client = None


def utc_now():
    return datetime.now(timezone.utc)


def admin_required(view):
    @wraps(view)
    def wrapped_view(*args, **kwargs):
        if session.get('admin_authenticated') is True:
            return view(*args, **kwargs)
        if request.path.startswith('/api/'):
            return jsonify({'success': False, 'message': 'Autenticación requerida'}), 401
        return redirect(url_for('login', next=request.full_path))
    return wrapped_view


def device_authenticated():
    """Enforce a device shared key only when DEVICE_API_KEY is configured."""
    expected = os.getenv('DEVICE_API_KEY')
    supplied = request.headers.get('X-Device-Key', '')
    return not expected or hmac.compare_digest(supplied, expected)


def get_devices_collection():
    global mongo_client
    mongo_uri = os.getenv('MONGODB_URI') or os.getenv('MONGO_URI')
    if not mongo_uri:
        raise RuntimeError('Falta configurar MONGODB_URI o MONGO_URI')
    if mongo_client is None:
        mongo_client = MongoClient(mongo_uri, serverSelectionTimeoutMS=5000)
        mongo_client.admin.command('ping')
    collection = mongo_client[os.getenv('MONGODB_DB', 'kiosqly')]['devices']
    collection.create_index([('device_id', ASCENDING)], unique=True)
    collection.create_index([('business_name', ASCENDING), ('location', ASCENDING)])
    collection.create_index([('last_seen', DESCENDING)])
    return collection


def serialise(value):
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, dict):
        return {key: serialise(item) for key, item in value.items()}
    if isinstance(value, list):
        return [serialise(item) for item in value]
    return value


def is_online(last_seen):
    if not isinstance(last_seen, datetime):
        return False
    # Los registros históricos de MongoDB pueden no incluir zona horaria.
    if last_seen.tzinfo is None:
        last_seen = last_seen.replace(tzinfo=timezone.utc)
    return (utc_now() - last_seen).total_seconds() < HEARTBEAT_TIMEOUT_SECONDS


def device_for_api(device):
    network = device.get('network', {})
    geo = device.get('location_geo', {})
    media = device.get('media', {})
    return serialise({
        'deviceId': device['device_id'], 'name': device.get('alias') or device.get('device_name') or device['device_id'],
        'businessName': device.get('business_name') or device.get('businessName') or 'Sin asignar',
        'location': device.get('location') or 'Sin sucursal', 'appVersion': device.get('app_version', 'N/D'),
        'status': 'ONLINE' if is_online(device.get('last_seen')) else 'OFFLINE', 'lastPing': device.get('last_seen'),
        'network': network, 'geo': geo, 'webviewUrl': device.get('webview_url') or device.get('current_url', ''),
        'lockState': device.get('lock_state', 'unknown'), 'media': media,
    })


def queue_command(device_id, command_type, payload=None):
    command = {'id': str(uuid4()), 'command': command_type, 'type': command_type, 'payload': payload or {}, 'created_at': utc_now()}
    result = get_devices_collection().update_one({'device_id': device_id}, {'$push': {'pending_commands': command}})
    if not result.matched_count:
        return None
    return serialise(command)


@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        if hmac.compare_digest(request.form.get('username', '').strip(), ADMIN_USERNAME) and hmac.compare_digest(request.form.get('password', ''), ADMIN_PASSWORD):
            session.clear(); session['admin_authenticated'] = True
            next_url = request.args.get('next') or url_for('home')
            return redirect(next_url if next_url.startswith('/') and not next_url.startswith('//') else url_for('home'))
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
    return render_template('index.html')


@app.route('/heartbeat', methods=['POST'])
def heartbeat():
    if not device_authenticated():
        return jsonify({'status': 'error', 'message': 'Dispositivo no autorizado'}), 401
    data = request.get_json(silent=True) or {}
    device_id = str(data.get('device_id', '')).strip()
    if not device_id:
        return jsonify({'status': 'error', 'message': 'device_id es requerido'}), 400
    forwarded = request.headers.get('X-Forwarded-For', request.remote_addr).split(',')[0].strip()
    now = utc_now()
    telemetry = {
        'last_seen': now, 'device_name': data.get('device_name', 'Tableta sin nombre'), 'app_version': data.get('app_version', 'N/D'),
        'business_name': data.get('business_name', data.get('businessName', 'Sin asignar')), 'location': data.get('location', 'Sin sucursal'),
        'current_url': data.get('current_url', ''), 'lock_state': data.get('lock_state', 'unknown'),
        'network': {'public_ip': forwarded, 'local_ip': data.get('local_ip', ''), 'type': data.get('network_type', ''), 'wifi_ssid': data.get('wifi_ssid', ''), 'signal_dbm': data.get('wifi_signal_strength')},
        'location_geo': {'latitude': data.get('latitude'), 'longitude': data.get('longitude'), 'accuracy_m': data.get('location_accuracy_m'), 'updated_at': now},
    }
    if data.get('alias') is not None:
        telemetry['alias'] = data['alias']
    coll = get_devices_collection()
    coll.update_one({'device_id': device_id}, {'$set': telemetry, '$setOnInsert': {'device_id': device_id, 'pending_commands': [], 'media': {}}}, upsert=True)
    previous = coll.find_one_and_update({'device_id': device_id}, {'$set': {'pending_commands': []}}, return_document=ReturnDocument.BEFORE)
    return jsonify({'status': 'ok', 'commands': serialise((previous or {}).get('pending_commands', []))})


@app.route('/api/v1/kiosks', methods=['GET'])
@admin_required
def list_kiosks():
    query = {}
    if request.args.get('business'):
        query['business_name'] = request.args['business']
    if request.args.get('location'):
        query['location'] = request.args['location']
    devices = [device_for_api(device) for device in get_devices_collection().find(query).sort('last_seen', DESCENDING)]
    return jsonify({'success': True, 'data': devices})


@app.route('/api/v1/fleet/options', methods=['GET'])
@admin_required
def fleet_options():
    coll = get_devices_collection()
    return jsonify({'success': True, 'businesses': sorted(coll.distinct('business_name')), 'locations': sorted(coll.distinct('location'))})


@app.route('/api/v1/kiosks/<device_id>', methods=['PATCH'])
@admin_required
def update_device(device_id):
    data = request.get_json(silent=True) or {}
    allowed = {'alias', 'business_name', 'location'}
    changes = {key: str(data[key]).strip() for key in allowed if key in data}
    if not changes:
        return jsonify({'success': False, 'message': 'No hay campos actualizables'}), 400
    result = get_devices_collection().update_one({'device_id': device_id}, {'$set': changes})
    if not result.matched_count:
        return jsonify({'success': False, 'message': 'Dispositivo no encontrado'}), 404
    return jsonify({'success': True})


@app.route('/api/v1/kiosks/<device_id>/command', methods=['POST'])
@admin_required
def send_command(device_id):
    data = request.get_json(silent=True) or {}
    command_type = data.get('type')
    payload = data.get('payload', {})
    if command_type not in COMMAND_TYPES or not isinstance(payload, dict):
        return jsonify({'success': False, 'message': 'Comando inválido'}), 400
    if command_type == 'set_url' and not str(payload.get('url', '')).startswith(('https://', 'http://')):
        return jsonify({'success': False, 'message': 'Se requiere una URL HTTP(S)'}), 400
    if command_type == 'update_app' and (not str(payload.get('url', '')).startswith('https://') or not str(payload.get('version', '')).strip()):
        return jsonify({'success': False, 'message': 'La actualización requiere URL HTTPS y versión'}), 400
    command = queue_command(device_id, command_type, payload)
    if not command:
        return jsonify({'success': False, 'message': 'Dispositivo no encontrado'}), 404
    return jsonify({'success': True, 'command': command}), 201


@app.route('/upload_image', methods=['POST'])
def upload_image():
    """Receives Android Base64 screenshots and camera snapshots.

    Request: {device_id, image_data, image_type: screenshot|camera_snapshot,
              captured_at?}. Images are capped at 5 MiB decoded, below MongoDB's
    16 MiB document cap. Move retained media to Blob before raising this limit.
    """
    if not device_authenticated():
        return jsonify({'success': False, 'message': 'Dispositivo no autorizado'}), 401
    data = request.get_json(silent=True) or {}
    device_id = str(data.get('device_id', '')).strip()
    media_type = data.get('image_type', data.get('type', 'screenshot'))
    encoded = str(data.get('image_data', '')).strip()
    if not device_id or media_type not in MEDIA_TYPES or not encoded:
        return jsonify({'success': False, 'message': 'device_id, image_type e image_data son requeridos'}), 400
    if ',' in encoded and encoded.startswith('data:'):
        encoded = encoded.split(',', 1)[1]
    try:
        image = base64.b64decode(encoded, validate=True)
    except (binascii.Error, ValueError):
        return jsonify({'success': False, 'message': 'image_data no es Base64 válido'}), 400
    if not image or len(image) > MAX_MEDIA_BYTES:
        return jsonify({'success': False, 'message': 'La imagen debe pesar entre 1 byte y 5 MiB'}), 413
    content_type = str(data.get('content_type', 'image/jpeg'))
    if content_type not in {'image/jpeg', 'image/png', 'image/webp'}:
        return jsonify({'success': False, 'message': 'content_type no permitido'}), 400
    captured_at = utc_now()
    media = {'data_url': f'data:{content_type};base64,{encoded}', 'captured_at': captured_at, 'content_type': content_type, 'size_bytes': len(image)}
    result = get_devices_collection().update_one({'device_id': device_id}, {'$set': {f'media.{media_type}': media}})
    if not result.matched_count:
        return jsonify({'success': False, 'message': 'Dispositivo no encontrado'}), 404
    return jsonify({'success': True, 'type': media_type, 'captured_at': captured_at.isoformat()}), 201


@app.route('/api/v1/devices/<device_id>/media', methods=['POST'])
def receive_media_url(device_id):
    # Backwards-compatible URL upload endpoint for a future object-storage client.
    if not device_authenticated():
        return jsonify({'success': False, 'message': 'Dispositivo no autorizado'}), 401
    data = request.get_json(silent=True) or {}
    media_type, media_url = data.get('type'), str(data.get('url', '')).strip()
    if media_type not in MEDIA_TYPES or not media_url.startswith('https://'):
        return jsonify({'success': False, 'message': 'Tipo o URL de medio inválidos'}), 400
    captured_at = utc_now()
    result = get_devices_collection().update_one({'device_id': device_id}, {'$set': {f'media.{media_type}': {'url': media_url, 'captured_at': captured_at}}})
    if not result.matched_count:
        return jsonify({'success': False, 'message': 'Dispositivo no encontrado'}), 404
    return jsonify({'success': True, 'captured_at': captured_at.isoformat()})
