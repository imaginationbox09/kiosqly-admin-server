import base64
import smtplib
import ssl
from email.message import EmailMessage
from functools import wraps
import os
import re
from uuid import uuid4
from datetime import datetime, timedelta, timezone
from flask import Flask, render_template, render_template_string, request, jsonify, redirect, session, url_for
from pymongo import ASCENDING, DESCENDING, MongoClient, ReturnDocument
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer
from werkzeug.security import check_password_hash, generate_password_hash
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
APPROVAL_EMAIL = 'info@kiosqly.com'
TRIAL_DAYS = 30


def get_users_collection():
    global mongo_client
    if mongo_client is None:
        get_devices_collection()
    database_name = os.getenv('MONGODB_DB', 'kiosqly')
    collection = mongo_client[database_name]['portal_users']
    collection.create_index([('email', ASCENDING)], unique=True)
    return collection


def approval_serializer():
    return URLSafeTimedSerializer(app.secret_key, salt='kiosqly-account-approval')


def send_approval_email(email):
    smtp_host = os.getenv('SMTP_HOST', 'gtxm1332.siteground.biz')
    smtp_user = os.getenv('SMTP_USER', 'info@kiosqly.com')
    smtp_password = os.getenv('SMTP_PASSWORD')
    if not smtp_host or not smtp_user or not smtp_password:
        raise RuntimeError('El correo no esta configurado. Define SMTP_HOST, SMTP_USER y SMTP_PASSWORD.')

    token = approval_serializer().dumps(email)
    base_url = os.getenv('PUBLIC_BASE_URL', request.url_root.rstrip('/'))
    approve_url = f'{base_url}{url_for("approve_account", token=token)}'
    reject_url = f'{base_url}{url_for("reject_account", token=token)}'

    message = EmailMessage()
    message['Subject'] = f'Nueva cuenta pendiente en Kiosqly: {email}'
    message['From'] = os.getenv('SMTP_FROM', smtp_user)
    message['To'] = APPROVAL_EMAIL
    message.set_content(
        f'La cuenta {email} solicito acceso al portal Kiosqly.\n\n'
        f'Aprobar: {approve_url}\n\n'
        f'Rechazar: {reject_url}\n\n'
        'Estos enlaces caducan en 24 horas.'
    )

    smtp_port = int(os.getenv('SMTP_PORT', '465'))
    smtp_use_tls = os.getenv('SMTP_USE_TLS', 'false').lower() == 'true'
    if smtp_use_tls:
        with smtplib.SMTP(smtp_host, smtp_port, timeout=15) as smtp:
            smtp.starttls(context=ssl.create_default_context())
            smtp.login(smtp_user, smtp_password)
            smtp.send_message(message)
    else:
        with smtplib.SMTP_SSL(smtp_host, smtp_port, timeout=15) as smtp:
            smtp.login(smtp_user, smtp_password)
            smtp.send_message(message)


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

def device_business_name(device):
    return str(
        device.get('assigned_business_name')
        or device.get('businessName')
        or device.get('business_name')
        or device.get('restaurant_id')
        or device.get('tenant')
        or 'Sin Asignar'
    ).strip() or 'Sin Asignar'


def device_location(device):
    return str(
        device.get('assigned_location')
        or device.get('location')
        or device.get('location_name')
        or device.get('site_address')
        or 'Ubicacion no registrada'
    ).strip() or 'Ubicacion no registrada'


def device_tablet_name(device):
    return str(
        device.get('assigned_tablet_name')
        or device.get('alias')
        or device.get('tablet_name')
        or device.get('device_name')
        or 'Tableta sin nombre'
    ).strip() or 'Tableta sin nombre'


def device_connection_status(device):
    last_seen = device.get('last_seen')
    if not last_seen:
        return False, None
    try:
        last_seen_at = last_seen if isinstance(last_seen, datetime) else datetime.fromisoformat(str(last_seen).replace('Z', '+00:00'))
        if last_seen_at.tzinfo is None:
            last_seen_at = last_seen_at.replace(tzinfo=timezone.utc)
        return (datetime.now(timezone.utc) - last_seen_at).total_seconds() < HEARTBEAT_TIMEOUT_SECONDS, last_seen_at
    except (TypeError, ValueError):
        return False, None


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


def get_support_collections():
    global mongo_client
    if mongo_client is None:
        get_devices_collection()
    database_name = os.getenv('MONGODB_DB', 'kiosqly')
    database = mongo_client[database_name]
    cases = database['support_cases']
    changes = database['change_logs']
    cases.create_index([('business_name', ASCENDING), ('created_at', DESCENDING)])
    changes.create_index([('business_name', ASCENDING), ('created_at', DESCENDING)])
    return cases, changes


def support_data_for_groups(grouped_devices):
    cases_collection, changes_collection = get_support_collections()
    support_data = {}
    for business_name in grouped_devices:
        key = business_name.casefold()
        cases = list(cases_collection.find({'business_name_key': key}).sort('created_at', DESCENDING))
        changes = list(changes_collection.find({'business_name_key': key}).sort('created_at', DESCENDING).limit(20))
        for item in cases + changes:
            item['_id'] = str(item.get('_id', ''))
            if isinstance(item.get('created_at'), datetime):
                item['created_at'] = item['created_at'].isoformat()
        support_data[business_name] = {'cases': cases, 'changes': changes}
    return support_data


def get_devices_for_dashboard():
    try:
        coll = get_devices_collection()
        raw_devices = list(coll.find({}))
        safe_devices = []
        for d in raw_devices:
            if isinstance(d, dict):
                d["_id"] = str(d.get("_id", ""))
                d['businessName'] = device_business_name(d)
                d['location'] = device_location(d)
                d['alias'] = device_tablet_name(d)
                d['is_online'], d['last_seen_at'] = device_connection_status(d)
                d['subscription'] = subscription_status(d)
                safe_devices.append(d)
            elif isinstance(d, str):
                safe_devices.append({"device_name": d, "device_id": d})
        return safe_devices
    except Exception as e:
        print("Error obteniendo dispositivos:", e)
        return []


def device_for_api(device_id, device):
    is_online, last_seen_at = device_connection_status(device)
    business_name = device_business_name(device)
    
    return {
        'deviceId': device_id,
        'restaurantId': device.get('restaurant_id', 'Sin asignar'),
        'businessName': business_name,
        'businessId': device.get('business_id'),
        'tenant': business_name,
        'name': device_tablet_name(device),
        'alias': device_tablet_name(device),
        'location': device_location(device),
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
        'lastPing': last_seen_at.isoformat() if last_seen_at else None,
        'status': 'ONLINE' if is_online else 'OFFLINE',
    }


@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    message = request.args.get('message')
    if request.method == 'POST':
        username = request.form.get('username', '').strip().lower()
        password = request.form.get('password', '')
        if username == ADMIN_USERNAME and check_password_hash(ADMIN_PASSWORD_HASH, password):
            session.clear()
            session['admin_authenticated'] = True
            next_url = request.args.get('next') or url_for('home')
            if not next_url.startswith('/') or next_url.startswith('//'):
                next_url = url_for('home')
            return redirect(next_url)
        user = get_users_collection().find_one({'email': username})
        if user and user.get('status') == 'approved' and check_password_hash(user['password_hash'], password):
            session.clear()
            session['admin_authenticated'] = True
            session['user_email'] = username
            next_url = request.args.get('next') or url_for('home')
            if not next_url.startswith('/') or next_url.startswith('//'):
                next_url = url_for('home')
            return redirect(next_url)
        if user and user.get('status') == 'pending':
            error = 'Tu cuenta esta pendiente de aprobacion.'
        else:
            error = 'Usuario o clave incorrectos.'
    return render_template('login.html', error=error, message=message)


@app.route('/register', methods=['GET', 'POST'])
def register():
    error = None
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        password_confirmation = request.form.get('password_confirmation', '')
        if not re.fullmatch(r'[^@\s]+@[^@\s]+\.[^@\s]+', email):
            error = 'Introduce un correo electronico valido.'
        elif len(password) < 8:
            error = 'La clave debe tener al menos 8 caracteres.'
        elif password != password_confirmation:
            error = 'Las claves no coinciden.'
        elif email == ADMIN_USERNAME.lower():
            error = 'Esta cuenta ya existe.'
        else:
            users = get_users_collection()
            existing_user = users.find_one({'email': email})
            if existing_user and existing_user.get('status') == 'approved':
                error = 'Esta cuenta ya existe.'
            elif existing_user and existing_user.get('status') == 'pending':
                error = 'Ya existe una solicitud pendiente para este correo.'
            else:
                users.insert_one({
                    'email': email,
                    'password_hash': generate_password_hash(password),
                    'status': 'pending',
                    'created_at': datetime.now(timezone.utc),
                })
                try:
                    send_approval_email(email)
                except Exception as email_error:
                    users.delete_one({'email': email, 'status': 'pending'})
                    print('Error enviando aprobacion:', email_error)
                    error = 'No se pudo enviar la solicitud. Revisa la configuracion de correo.'
                else:
                    return redirect(url_for('login', message='Solicitud enviada. Te avisaremos cuando sea aprobada.'))
    return render_template('login.html', error=error, register_mode=True)


def process_account_decision(token, status):
    try:
        email = approval_serializer().loads(token, max_age=86400)
    except (BadSignature, SignatureExpired):
        return render_template('login.html', error='El enlace de aprobacion no es valido o ya caduco.')
    users = get_users_collection()
    result = users.update_one({'email': email, 'status': 'pending'}, {'$set': {
        'status': status,
        'reviewed_at': datetime.now(timezone.utc),
    }})
    if result.matched_count == 0:
        return render_template('login.html', message='Esta solicitud ya fue procesada.')
    decision = 'aprobada' if status == 'approved' else 'rechazada'
    return render_template('login.html', message=f'La cuenta de {email} fue {decision}.')


@app.route('/account/approve/<token>')
def approve_account(token):
    return process_account_decision(token, 'approved')


@app.route('/account/reject/<token>')
def reject_account(token):
    return process_account_decision(token, 'rejected')


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
        b_name = device_business_name(dev)
        existing_name = next((name for name in grouped_devices if name.casefold() == b_name.casefold()), b_name)
        grouped_devices[existing_name].append(dev)
        
    try:
        support_data = support_data_for_groups(grouped_devices)
    except Exception as error:
        print('Error obteniendo soporte:', error)
        support_data = {name: {'cases': [], 'changes': []} for name in grouped_devices}
    return render_template(
        "index.html",
        devices=devices,
        grouped_devices=dict(grouped_devices),
        support_data=support_data,
    )


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
        {'$set': {**telemetry, 'pending_commands': []}, '$setOnInsert': {
            'device_id': device_id,
            'created_at': now,
            'businessName': data.get('businessName', data.get('business_name', data.get('restaurant_id', 'Sin Asignar'))),
            'location': data.get('location', data.get('site_address', 'Ubicacion no registrada')),
        }},
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
        collection = get_devices_collection()
        previous = collection.find_one({'device_id': device_id}) or {}
        previous_business = device_business_name(previous)
        previous_values = {
            'business_name': previous_business,
            'tablet_name': device_tablet_name(previous),
            'location': device_location(previous),
        }
        new_values = {
            'business_name': business_name or 'Sin Asignar',
            'tablet_name': tablet_name or 'Tableta sin nombre',
            'location': location_name or 'Ubicacion no registrada',
        }
        collection.update_one(
            {'device_id': device_id},
            {
                '$set': {
                    'assigned_business_name': business_name,
                    'business_name': business_name,
                    'businessName': business_name,
                    'assigned_tablet_name': tablet_name,
                    'alias': tablet_name,
                    'tablet_name': tablet_name,
                    'assigned_location': location_name,
                    'location_name': location_name,
                    'location': location_name
                }
            }
        )
        if created_at:
            collection.update_one(
                {'device_id': device_id}, {'$set': {'created_at': created_at}}
            )
        changed_fields = {
            field: {'from': previous_values[field], 'to': new_values[field]}
            for field in previous_values
            if previous_values[field] != new_values[field]
        }
        if changed_fields:
            _, changes_collection = get_support_collections()
            changes_collection.insert_one({
                'change_id': str(uuid4()),
                'business_name': new_values['business_name'],
                'business_name_key': new_values['business_name'].casefold(),
                'device_id': device_id,
                'device_name': new_values['tablet_name'],
                'changed_fields': changed_fields,
                'created_at': datetime.now(timezone.utc),
                'changed_by': ADMIN_USERNAME,
            })
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


@app.route('/api/support-cases', methods=['POST'])
@admin_required
def create_support_case():
    data = request.get_json(silent=True) or {}
    business_name = str(data.get('business_name', '')).strip()
    title = str(data.get('title', '')).strip()
    description = str(data.get('description', '')).strip()
    priority = str(data.get('priority', 'medium')).lower().strip()
    device_id = str(data.get('device_id', '')).strip()
    if not business_name or not title or not description:
        return jsonify({'success': False, 'message': 'Negocio, titulo y descripcion son requeridos'}), 400
    if priority not in {'low', 'medium', 'high', 'urgent'}:
        priority = 'medium'
    now = datetime.now(timezone.utc)
    case = {
        'case_id': str(uuid4()),
        'business_name': business_name,
        'business_name_key': business_name.casefold(),
        'device_id': device_id,
        'title': title,
        'description': description,
        'priority': priority,
        'status': 'open',
        'created_at': now,
        'updated_at': now,
        'created_by': ADMIN_USERNAME,
    }
    cases_collection, _ = get_support_collections()
    cases_collection.insert_one(case)
    return jsonify({'success': True, 'case_id': case['case_id']}), 201


@app.route('/api/support-cases/<case_id>', methods=['PATCH'])
@admin_required
def update_support_case(case_id):
    data = request.get_json(silent=True) or {}
    status = str(data.get('status', '')).lower().strip()
    if status not in {'open', 'in_progress', 'resolved', 'closed'}:
        return jsonify({'success': False, 'message': 'Estado no valido'}), 400
    cases_collection, _ = get_support_collections()
    result = cases_collection.update_one(
        {'case_id': case_id},
        {'$set': {'status': status, 'updated_at': datetime.now(timezone.utc)}}
    )
    if not result.matched_count:
        return jsonify({'success': False, 'message': 'Caso no encontrado'}), 404
    return jsonify({'success': True}), 200


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
