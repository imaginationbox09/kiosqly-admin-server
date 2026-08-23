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
        .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 20px; }
        .card { background: white; border-radius: 10px; padding: 20px; box-shadow: 0 4px 6px rgba(0,0,0,0.05); border-top: 4px solid #007bff; }
        .card h3 { margin-top: 0; color: #007bff; display: flex; justify-content: space-between; }
        .info-group { margin-bottom: 12px; font-size: 14px; }
        .info-group label { font-weight: bold; color: #666; display: block; margin-bottom: 2px; }
        .battery-bar { background: #e0e0e0; border-radius: 10px; height: 12px; overflow: hidden; margin-top: 4px; }
        .battery-fill { background: #28a745; height: 100%; transition: width 0.3s; }
        .url-form { margin-top: 15px; display: flex; gap: 8px; }
        .url-input { flex: 1; padding: 8px; border: 1px solid #ccc; border-radius: 4px; font-size: 13px; }
        .btn { background: #007bff; color: white; border: none; padding: 8px 12px; border-radius: 4px; cursor: pointer; font-weight: bold; font-size: 13px; }
        .btn:hover { background: #0056b3; }
        .btn-reload { background: #6c757d; }
        .map-link { color: #007bff; text-decoration: none; font-weight: bold; }
        .map-link:hover { text-decoration: underline; }
        .empty-state { background: white; padding: 40px; text-align: center; border-radius: 10px; color: #777; }
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
                <a href="/" class="btn btn-reload" style="margin-left: 10px; text-decoration: none;">🔄 Refrescar</a>
            </div>
        </div>

        <h2>Dispositivos Conectados ({{ devices|length }})</h2>

        {% if devices %}
            <div class="grid">
                {% for device_id, info in devices.items() %}
                <div class="card">
                    <h3>
                        <span>{{ info.get('device_name', 'Tableta sin Nombre') }}</span>
                    </h3>
                    
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

    # Crear o actualizar el registro de la tableta
    if device_id not in devices_db:
        devices_db[device_id] = {
            'target_url': None
        }

    # Actualizar datos recibidos de la app de la tableta
    devices_db[device_id]['device_name'] = data.get('device_name', 'Tableta Desconocida')
    devices_db[device_id]['battery'] = data.get('battery', 0)
    devices_db[device_id]['current_url'] = data.get('current_url', 'N/A')
    devices_db[device_id]['latitude'] = data.get('latitude')
    devices_db[device_id]['longitude'] = data.get('longitude')

    # Responder a la tableta enviando comandos pendientes (ej. nueva URL)
    response_data = {'status': 'ok'}
    
    if devices_db[device_id].get('target_url'):
        response_data['url'] = devices_db[device_id]['target_url']
        # Limpiar la URL pendiente una vez enviada
        devices_db[device_id]['target_url'] = None

    return jsonify(response_data), 200

@app.route('/set_url', methods=['POST'])
def set_url():
    device_id = request.form.get('device_id')
    target_url = request.form.get('target_url')

    if device_id in devices_db and target_url:
        devices_db[device_id]['target_url'] = target_url

    return render_template_string('<script>alert("URL enviada a la tableta correctamente."); window.location.href="/";</script>')

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
