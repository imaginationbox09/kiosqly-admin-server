import base64
import os
from datetime import datetime, timezone
from flask import Flask, render_template_string, request, jsonify
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

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Panel de Control Avanzado - Kiosqly</title>
    <style>
        body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #f4f6f9; margin: 20px; color: #333; }
        .container { max-width: 1200px; margin: 0 auto; }
        .header { display: flex; justify-content: space-between; align-items: center; background: white; padding: 20px; border-radius: 10px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); margin-bottom: 20px; }
        h1 { margin: 0; font-size: 24px; }
        .status-badge { background: #e8f5e9; color: #2e7d32; padding: 6px 12px; border-radius: 20px; font-weight: bold; font-size: 14px; }
        .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(360px, 1fr)); gap: 20px; }
        .card { background: white; border-radius: 10px; padding: 20px; box-shadow: 0 4px 6px rgba(0,0,0,0.05); border-top: 4px solid #007bff; }
        .card-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 15px; }
        .card h3 { margin: 0; color: #007bff; font-size: 18px; }
        .header-btns { display: flex; gap: 5px; flex-wrap: wrap; }
        .info-group { margin-bottom: 12px; font-size: 13px; }
        .info-group label { font-weight: bold; color: #666; display: block; margin-bottom: 2px; }
        .battery-bar { background: #e0e0e0; border-radius: 10px; height: 12px; overflow: hidden; margin-top: 4px; }
        .battery-fill { background: #28a745; height: 100%; transition: width 0.3s; }
        .control-form { margin-top: 10px; display: flex; gap: 6px; }
        .input-text { flex: 1; padding: 6px 8px; border: 1px solid #ccc; border-radius: 4px; font-size: 12px; }
        .btn { background: #007bff; color: white; border: none; padding: 6px 10px; border-radius: 4px; cursor: pointer; font-weight: bold; font-size: 12px; text-decoration: none; }
        .btn:hover { background: #0056b3; }
        .btn-reload-panel { background: #6c757d; }
        .btn-action { background: #ffc107; color: #212529; font-size: 11px; padding: 5px 8px; border-radius: 4px; border: none; cursor: pointer; font-weight: bold; }
        .btn-action:hover { background: #e0a800; }
        .btn-camera { background: #17a2b8; color: white; }
        .btn-camera:hover { background: #138496; }
        .btn-danger { background: #dc3545; color: white; }
        .btn-danger:hover { background: #bd2130; }
        .btn-success { background: #28a745; color: white; }
        .ip-badge { background: #f8f9fa; border: 1px solid #e9ecef; padding: 3px 6px; border-radius: 4px; font-family: monospace; font-size: 11px; }
        .metric-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; background: #f8f9fa; padding: 8px; border-radius: 6px; margin-bottom: 10px; }
        .captured-photo { width: 100%; max-height: 200px; object-fit: cover; border-radius: 6px; margin-top: 8px; border: 1px solid #ddd; }
        .section-title { font-weight: bold; color: #495057; border-bottom: 1px solid #dee2e6; padding-bottom: 4px; margin-top: 12px; margin-bottom: 8px; font-size: 12px; text-transform: uppercase; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <div>
                <h1>Kiosqly Control Panel Pro 🚀</h1>
                <small>Servidor de Control Remoto y Telemetría de Tabletas</small>
            </div>
            <div>
                <span class="status-badge">En Línea</span>
                <a href="/" class="btn btn-reload-panel" style="margin-left: 10px;">🔄 Refrescar Panel</a>
            </div>
        </div>

        <h2>Dispositivos Conectados ({{ devices|length }})</h2>

        {% if devices %}
            <div class="grid">
                {% for device_id, info in devices.items() %}
                <div class="card">
                    <div class="card-header">
                        <h3>{{ info.get('device_name', 'Tableta sin Nombre') }}</h3>
                        <span style="font-size: 11px; color: #6c757d;">v{{ info.get('app_version', '1.0.0') }}</span>
                    </div>

                    <!-- Botones de Acción Rápida -->
                    <div class="header-btns" style="margin-bottom: 12px;">
                        <form action="/send_cmd" method="POST" style="margin: 0;">
                            <input type="hidden" name="device_id" value="{{ device_id }}">
                            <input type="hidden" name="command" value="reload">
                            <button type="submit" class="btn-action">🔄 Recargar</button>
                        </form>
                        <form action="/send_cmd" method="POST" style="margin: 0;">
                            <input type="hidden" name="device_id" value="{{ device_id }}">
                            <input type="hidden" name="command" value="clear_cache">
                            <button type="submit" class="btn-action" style="background: #e2e3e5;">🧹 Limpiar Caché</button>
                        </form>
                        <form action="/send_cmd" method="POST" style="margin: 0;">
                            <input type="hidden" name="device_id" value="{{ device_id }}">
                            <input type="hidden" name="command" value="capture_camera">
                            <button type="submit" class="btn-action btn-camera">📸 Cámara</button>
                        </form>
                        <form action="/send_cmd" method="POST" style="margin: 0;">
                            <input type="hidden" name="device_id" value="{{ device_id }}">
                            <input type="hidden" name="command" value="take_screenshot">
                            <button type="submit" class="btn-action" style="background: #6f42c1; color: white;">🖥️ Capturar Pantalla</button>
                        </form>
                        <form action="/send_cmd" method="POST" style="margin: 0;">
                            <input type="hidden" name="device_id" value="{{ device_id }}">
                            <input type="hidden" name="command" value="reboot_app">
                            <button type="submit" class="btn-action btn-danger" onclick="return confirm('¿Reiniciar app remota?')">⚡ Reiniciar App</button>
                        </form>
                    </div>

                    <!-- Telemetría y Recursos del Dispositivo -->
                    <div class="metric-grid">
                        <div><strong>Batería:</strong> {{ info.get('battery', 0) }}% {% if info.get('is_charging') %}⚡{% endif %}</div>
                        <div><strong>RAM Libre:</strong> {{ info.get('ram_free_mb', 'N/A') }} MB</div>
                        <div><strong>Almacenamiento:</strong> {{ info.get('storage_free_mb', 'N/A') }} MB</div>
                        <div><strong>Red:</strong> {{ info.get('network_type', 'N/A') }} ({{ info.get('wifi_signal_strength', 'N/A') }}%)</div>
                    </div>

                    <div class="info-group">
                        <label>Identificador Único:</label>
                        <code>{{ device_id }}</code>
                    </div>

                    <div class="info-group">
                        <label>Conectividad IP:</label>
                        <div style="display: flex; gap: 6px; margin-top: 2px;">
                            <span class="ip-badge"><strong>Wi-Fi:</strong> {{ info.get('local_ip', 'N/A') }}</span>
                            <span class="ip-badge"><strong>Pública:</strong> {{ info.get('public_ip', 'N/A') }}</span>
                        </div>
                    </div>

                    <div class="info-group">
                        <label>URL Actual en Pantalla:</label>
                        <small style="word-break: break-all; color: #28a745; font-weight: bold;">{{ info.get('current_url', 'N/A') }}</small>
                    </div>

                    {% if info.get('last_image') %}
                    <div class="info-group">
                        <label>Última Captura Recibida:</label>
                        <img src="data:image/jpeg;base64,{{ info.last_image }}" class="captured-photo" alt="Captura Remota">
                    </div>
                    {% endif %}

                    <!-- SECCIÓN DE CONTROLES REMOTOS -->
                    <div class="section-title">Controles Remotos</div>

                    <!-- Cambiar Navegación URL -->
                    <form action="/send_cmd" method="POST" class="control-form">
                        <input type="hidden" name="device_id" value="{{ device_id }}">
                        <input type="hidden" name="command" value="set_url">
                        <input type="url" name="target_url" class="input-text" placeholder="https://nueva-url.com" required>
                        <button type="submit" class="btn">Cambiar URL</button>
                    </form>

                    <!-- Configurar Red Wi-Fi Remota -->
                    <form action="/send_cmd" method="POST" class="control-form">
                        <input type="hidden" name="device_id" value="{{ device_id }}">
                        <input type="hidden" name="command" value="change_wifi">
                        <input type="text" name="wifi_ssid" class="input-text" placeholder="Nombre Wi-Fi (SSID)" required>
                        <input type="password" name="wifi_pass" class="input-text" placeholder="Contraseña" required>
                        <button type="submit" class="btn btn-success">Cambiar Wi-Fi</button>
                    </form>

                    <!-- Ajuste de Brillo y Volumen -->
                    <div style="display: flex; gap: 6px; margin-top: 6px;">
                        <form action="/send_cmd" method="POST" class="control-form" style="flex: 1;">
                            <input type="hidden" name="device_id" value="{{ device_id }}">
                            <input type="hidden" name="command" value="set_brightness">
                            <input type="number" min="0" max="255" name="brightness" class="input-text" placeholder="Brillo (0-255)" required>
                            <button type="submit" class="btn" style="background: #ff9800;">Brillo</button>
                        </form>
                        <form action="/send_cmd" method="POST" class="control-form" style="flex: 1;">
                            <input type="hidden" name="device_id" value="{{ device_id }}">
                            <input type="hidden" name="command" value="set_volume">
                            <input type="number" min="0" max="100" name="volume" class="input-text" placeholder="Vol (0-100)" required>
                            <button type="submit" class="btn" style="background: #673ab7;">Volumen</button>
                        </form>
                    </div>

                </div>
                {% endfor %}
            </div>
        {% else %}
            <div style="background: white; padding: 40px; text-align: center; border-radius: 10px; color: #777;">
                <p>No hay tabletas registradas en este momento. Esperando la conexión del kiosco...</p>
            </div>
        {% endif %}
    </div>
</body>
</html>
"""

@app.route('/')
def home():
    return render_template_string(HTML_TEMPLATE, devices=get_devices_for_dashboard())

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