import base64
import os
from flask import Flask, render_template_string, request, jsonify

app = Flask(__name__)

# Memoria para almacenar múltiples dispositivos por su ID
devices_db = {}

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Panel de Control - Kiosqly</title>
    <style>
        body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #f4f6f9; margin: 20px; color: #333; }
        .container { max-width: 1000px; margin: 0 auto; }
        .header { display: flex; justify-content: space-between; align-items: center; background: white; padding: 20px; border-radius: 10px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); margin-bottom: 20px; }
        h1 { margin: 0; font-size: 24px; }
        .status-badge { background: #e8f5e9; color: #2e7d32; padding: 6px 12px; border-radius: 20px; font-weight: bold; font-size: 14px; }
        .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(320px, 1fr)); gap: 20px; }
        .card { background: white; border-radius: 10px; padding: 20px; box-shadow: 0 4px 6px rgba(0,0,0,0.05); border-top: 4px solid #007bff; }
        .card-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 15px; }
        .card h3 { margin: 0; color: #007bff; }
        .header-btns { display: flex; gap: 5px; }
        .info-group { margin-bottom: 12px; font-size: 14px; }
        .info-group label { font-weight: bold; color: #666; display: block; margin-bottom: 2px; }
        .battery-bar { background: #e0e0e0; border-radius: 10px; height: 12px; overflow: hidden; margin-top: 4px; }
        .battery-fill { background: #28a745; height: 100%; transition: width 0.3s; }
        .url-form { margin-top: 15px; display: flex; gap: 8px; }
        .url-input { flex: 1; padding: 8px; border: 1px solid #ccc; border-radius: 4px; font-size: 13px; }
        .btn { background: #007bff; color: white; border: none; padding: 8px 12px; border-radius: 4px; cursor: pointer; font-weight: bold; font-size: 13px; text-decoration: none; }
        .btn:hover { background: #0056b3; }
        .btn-reload { background: #6c757d; }
        .btn-action { background: #ffc107; color: #212529; font-size: 12px; padding: 6px 10px; border-radius: 4px; border: none; cursor: pointer; font-weight: bold; }
        .btn-action:hover { background: #e0a800; }
        .btn-camera { background: #17a2b8; color: white; }
        .btn-camera:hover { background: #138496; }
        .map-link { color: #007bff; text-decoration: none; font-weight: bold; }
        .map-link:hover { text-decoration: underline; }
        .empty-state { background: white; padding: 40px; text-align: center; border-radius: 10px; color: #777; }
        .captured-photo { width: 100%; max-height: 200px; object-fit: cover; border-radius: 6px; margin-top: 8px; border: 1px solid #ddd; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <div>
                <h1>Kiosqly Control Panel 🚀</h1>
                <small>Servidor de Administración de Tabletas</small>
            </div>
            <div>
                <span class="status-badge">En Línea (Render)</span>
                <a href="/" class="btn btn-reload" style="margin-left: 10px;">🔄 Refrescar Panel</a>
            </div>
        </div>

        <h2>Dispositivos Conectados ({{ devices|length }})</h2>

        {% if devices %}
            <div class="grid">
                {% for device_id, info in devices.items() %}
                <div class="card">
                    <div class="card-header">
                        <h3>{{ info.get('device_name', 'Tableta sin Nombre') }}</h3>
                        <div class="header-btns">
                            <form action="/reload_device" method="POST" style="margin: 0; display: inline;">
                                <input type="hidden" name="device_id" value="{{ device_id }}">
                                <button type="submit" class="btn-action" title="Forzar recarga del sitio en la tableta">🔄 Recargar</button>
                            </form>
                            <form action="/capture_camera" method="POST" style="margin: 0; display: inline;">
                                <input type="hidden" name="device_id" value="{{ device_id }}">
                                <button type="submit" class="btn-action btn-camera" title="Solicitar foto remota desde la cámara">📸 Foto</button>
                            </form>
                        </div>
                    </div>
                    
                    <div class="info-group">
                        <label>ID del Dispositivo:</label>
                        <code>{{ device_id }}</code>
                    </div>

                    <div class="info-group">
                        <label>Batería ({{ info.get('battery', 0) }}%):</label>
                        <div class="battery-bar">
                            <div class="battery-fill" style="width: {{ info.get('battery', 0) }}%;"></div>
                        </div>
                    </div>

                    <div class="info-group">
                        <label>Ubicación Exacta:</label>
                        {% if info.get('latitude') and info.get('longitude') %}
                            📍 <a href="https://www.google.com/maps?q={{ info.latitude }},{{ info.longitude }}" target="_blank" class="map-link">
                                Ver en Google Maps ({{ info.latitude }}, {{ info.longitude }})
                            </a>
                        {% else %}
                            <span style="color: #999;">Ubicación no disponible</span>
                        {% endif %}
                    </div>

                    <div class="info-group">
                        <label>URL Actual en Pantalla:</label>
                        <small style="word-break: break-all; color: #28a745; font-weight: bold;">{{ info.get('current_url', 'N/A') }}</small>
                    </div>

                    {% if info.get('last_image') %}
                    <div class="info-group">
                        <label>Última Captura Recibida:</label>
                        <img src="data:image/jpeg;base64,{{ info.last_image }}" class="captured-photo" alt="Captura remota">
                    </div>
                    {% endif %}

                    <form action="/set_url" method="POST" class="url-form">
                        <input type="hidden" name="device_id" value="{{ device_id }}">
                        <input type="url" name="target_url" class="url-input" placeholder="https://nueva-url.com" required>
                        <button type="submit" class="btn">Cambiar URL</button>
                    </form>
                </div>
                {% endfor %}
            </div>
        {% else %}
            <div class="empty-state">
                <p>No hay tabletas registradas en este momento. Esperando la primera conexión del kiosco...</p>
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

    if device_id not in devices_db:
        devices_db[device_id] = {
            'target_url': None,
            'should_reload': False,
            'capture_image': False,
            'last_image': None
        }

    devices_db[device_id]['device_name'] = data.get('device_name', 'Tableta Desconocida')
    devices_db[device_id]['battery'] = data.get('battery', 0)
    devices_db[device_id]['current_url'] = data.get('current_url', 'N/A')
    devices_db[device_id]['latitude'] = data.get('latitude')
    devices_db[device_id]['longitude'] = data.get('longitude')

    response_data = {'status': 'ok'}
    
    # Comando para tomar foto si se presionó el botón 📸 Foto
    if devices_db[device_id].get('capture_image'):
        response_data['capture_image'] = True
        devices_db[device_id]['capture_image'] = False

    # Comando para recargar página
    if devices_db[device_id].get('should_reload'):
        response_data['reload_page'] = True
        devices_db[device_id]['should_reload'] = False

    # Comando para cambiar URL
    if devices_db[device_id].get('target_url'):
        response_data['url'] = devices_db[device_id]['target_url']
        devices_db[device_id]['target_url'] = None

    return jsonify(response_data), 200

@app.route('/upload_image', methods=['POST'])
def upload_image():
    data = request.get_json(silent=True) or {}
    device_id = data.get('device_id')
    image_data = data.get('image_data')

    if device_id in devices_db and image_data:
        devices_db[device_id]['last_image'] = image_data
        print(f"¡Foto remota recibida con éxito del dispositivo {device_id}!")
        return jsonify({'status': 'photo_received'}), 200

    return jsonify({'status': 'no_image_or_device'}), 400

@app.route('/set_url', methods=['POST'])
def set_url():
    device_id = request.form.get('device_id')
    target_url = request.form.get('target_url')

    if device_id in devices_db and target_url:
        devices_db[device_id]['target_url'] = target_url

    return render_template_string('<script>alert("URL enviada a la tableta correctamente."); window.location.href="/";</script>')

@app.route('/reload_device', methods=['POST'])
def reload_device():
    device_id = request.form.get('device_id')

    if device_id in devices_db:
        devices_db[device_id]['should_reload'] = True

    return render_template_string('<script>alert("Orden de recarga enviada a la tableta."); window.location.href="/";</script>')

@app.route('/capture_camera', methods=['POST'])
def capture_camera():
    device_id = request.form.get('device_id')

    if device_id in devices_db:
        devices_db[device_id]['capture_image'] = True

    return render_template_string('<script>alert("Solicitud de foto enviada a la tableta."); window.location.href="/";</script>')

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
