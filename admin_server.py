import base64
from functools import wraps
import os
from datetime import datetime, timedelta, timezone
from flask import Flask, render_template, render_template_string, request, jsonify, redirect, session, url_for
from pymongo import ASCENDING, DESCENDING, MongoClient, ReturnDocument
from werkzeug.security import check_password_hash
from collections import defaultdict

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
    'scrypt:32768:8:1$FQYXwsblRUjXqVzu$3695cc64c72da2704cd76f2fc4ae196ab6d085d6c4def647f871ead2096189b7e3ecbc916cdf6cfffc342f853b66e659ebb2f2753adec7600fb50944bca0d920'
)
TRIAL_DAYS = 30


def parse_created_at(value):
    if isinstance(value, datetime):
        created_at = value
    elif value:
        try:
            created_at = datetime.fromisoformat(str(value).replace('Z', '+00:00'))
        except ValueError:
            return None
    else:
        return None
    return created_at.replace(tzinfo=timezone.utc) if created_at.tzinfo is None else created_at


def subscription_status(device):
    created_at = parse_created_at(
        device.get('created_at') or device.get('registration_date') or device.get('createdAt')
    )
    if created_at is None:
        created_at = parse_created_at(device.get('last_seen')) or datetime.now(timezone.utc)
    expires_at = created_at + timedelta(days=TRIAL_DAYS)
    days_remaining = max(0, (expires_at.date() - datetime.now(timezone.utc).date()).days)
    return {
        'createdAt': created_at.date().isoformat(),
        'expiresAt': expires_at.date().isoformat(),
        'daysRemaining': days_remaining,
        'isExpired': days_remaining == 0 and datetime.now(timezone.utc) >= expires_at,
    }


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
                d['subscription'] = subscription_status(d)
                safe_devices.append(d)
            elif isinstance(d, str):
                safe_devices.append({"device_name": d, "device_id": d})
        return safe_devices
    except Exception as e:
        print("Error obteniendo dispositivos:", e)
        return []


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
    
    business_name = device.get('businessName') or device.get('restaurant_id') or device.get('business_name') or device.get('tenant') or 'Sin Asignar'
    
    return {
        'deviceId': device_id,
        'restaurantId': device.get('restaurant_id', 'Sin asignar'),
        'businessName': business_name,
        'businessId': device.get('business_id'),
        'tenant': business_name,
        'name': device.get('alias') or device.get('device_name', 'Tableta sin nombre'),
        'alias': device.get('alias', ''),
        'location': device.get('location', 'Ubicacion no registrada'),
        'createdAt': subscription_status(device)['createdAt'],
        'subscription': subscription_status(device),
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
    devices = get_devices_for_dashboard()
    
    grouped_devices = defaultdict(list)
    for dev in devices:
        b_name = dev.get('businessName') or dev.get('restaurant_id') or 'Sin Asignar'
        grouped_devices[b_name].append(dev)
        
    return render_template("index.html", devices=devices, grouped_devices=dict(grouped_devices))


@app.route('/heartbeat', methods=['POST'])
def heartbeat():
    data = request.get_json(silent=True) or {}
    device_id = data.get("device_id")

    if not device_id:
        return jsonify({'status': 'error', 'message': 'device_id missing'}), 400

    public_ip = request.headers.get('X-Forwarded-For', request.remote_addr)
    if public_ip and ',' in public_ip:
        public_ip = public_ip.split(',')[0].strip()

    now = datetime.now(timezone.utc)
    telemetry = {
        'last_seen': now,
        'device_name': data.get('device_name', 'Tableta Desconocida'),
        'restaurant_id': data.get('restaurant_id', data.get('restaurantId', 'Sin asignar')),
        'businessName': data.get('businessName', data.get('business_name', data.get('restaurant_id', 'Sin Asignar'))),
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
        {'$set': {**telemetry, 'pending_commands': []}, '$setOnInsert': {'device_id': device_id, 'created_at': now}},
        upsert=True,
        return_document=ReturnDocument.BEFORE
    )

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


@app.route('/api/device/<device_id>/update', methods=['POST'])
@admin_required
def update_device_info(device_id):
    data = request.json or request.form
    business_name = str(data.get('business_name', '')).strip()
    tablet_name = str(data.get('tablet_name', data.get('alias', ''))).strip()
    location_name = str(data.get('location_name', data.get('location', ''))).strip()
    created_at = parse_created_at(data.get('created_at'))
    if data.get('created_at') and created_at is None:
        return {'success': False, 'error': 'La fecha de alta no es valida.'}, 400
    
    try:
        get_devices_collection().update_one(
            {'device_id': device_id},
            {
                '$set': {
                    'business_name': business_name,
                    'businessName': business_name,
                    'alias': tablet_name,
                    'tablet_name': tablet_name,
                    'location_name': location_name,
                    'location': location_name
                }
            }
        )
        if created_at:
            get_devices_collection().update_one(
                {'device_id': device_id}, {'$set': {'created_at': created_at}}
            )
        return {'success': True, 'message': 'Dispositivo actualizado correctamente'}
    except Exception as e:
        return {'success': False, 'error': str(e)}, 500


@app.route('/api/business-names', methods=['GET'])
@admin_required
def generate_business_names():
    category = request.args.get('category', 'retail').strip().lower()
    query = request.args.get('query', '').strip()
    names_by_category = {
        'retail': ['Punto Central', 'Casa Mercado', 'Compra Viva', 'Nexo Comercial', 'La Canasta Urbana'],
        'restaurant': ['Sabor de Barrio', 'Mesa Abierta', 'Fogon Central', 'Cuchara Viva', 'La Terraza Local'],
        'restaurante': ['Sabor de Barrio', 'Mesa Abierta', 'Fogon Central', 'Cuchara Viva', 'La Terraza Local'],
    }
    names = names_by_category.get(category, names_by_category['retail'])
    if query:
        names = [f'{query.title()} {suffix}' for suffix in ('Market', 'Casa', 'Express', 'Local', 'Central')]
    return jsonify({'success': True, 'category': category, 'names': names})


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
