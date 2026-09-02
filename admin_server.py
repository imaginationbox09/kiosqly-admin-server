import base64
import os
from flask import Flask, render_template_string, request, jsonify

app = Flask(__name__)

# Memoria temporal para almacenar las tabletas conectadas
devices_db = {}

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
    return render_template_string(HTML_TEMPLATE, devices=devices_db)

@app.route('/heartbeat', methods=['POST'])
def heartbeat():
    data = request.get_json(silent=True) or {}
    device_id = data.get("device_id")

    if not device_id:
        return jsonify({'status': 'error', 'message': 'device_id missing'}), 400

    public_ip = request.headers.get('X-Forwarded-For', request.remote_addr)
    if public_ip and ',' in public_ip:
        public_ip = public_ip.split(',')[0].strip()

    if device_id not in devices_db:
        devices_db[device_id] = {'pending_commands': []}

    # Actualizar telemetría completa
    devices_db[device_id].update({
        'device_name': data.get('device_name', 'Tableta Desconocida'),
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
    })

    # Preparar respuesta con comandos pendientes para la tableta
    response_data = {'status': 'ok', 'commands': devices_db[device_id].get('pending_commands', [])}
    
    # Vaciar cola de comandos tras entregarlos
    devices_db[device_id]['pending_commands'] = []

    return jsonify(response_data), 200

@app.route('/upload_image', methods=['POST'])
def upload_image():
    data = request.get_json(silent=True) or {}
    device_id = data.get('device_id')
    image_data = data.get('image_data')

    if device_id in devices_db and image_data:
        devices_db[device_id]['last_image'] = image_data
        return jsonify({'status': 'photo_received'}), 200

    return jsonify({'status': 'no_image_or_device'}), 400

@app.route('/send_cmd', methods=['POST'])
def send_cmd():
    device_id = request.form.get('device_id')
    command = request.form.get('command')

    if device_id in devices_db:
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

        devices_db[device_id].setdefault('pending_commands', []).append(cmd_payload)

    return render_template_string('<script>alert("Comando enviado a la tableta."); window.location.href="/";</script>')

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)