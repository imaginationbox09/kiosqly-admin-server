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
    <title>Kiosqly Control Panel</title>
    <style>
        body { font-family: Arial, sans-serif; background: #f4f6f9; padding: 20px; margin: 0; }
        h2 { color: #333; margin-bottom: 20px; }
        .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(320px, 1fr)); gap: 20px; }
        .card { background: white; border-radius: 10px; padding: 20px; box-shadow: 0 4px 6px rgba(0,0,0,0.05); border-top: 4px solid #007bff; }
        .card h3 { margin: 0 0 15px 0; color: #007bff; font-size: 18px; }
        .info-group { margin-bottom: 12px; font-size: 14px; }
        .info-group label { font-weight: bold; color: #666; display: block; margin-bottom: 2px; }
        .empty-state { background: white; padding: 40px; text-align: center; border-radius: 10px; color: #777; grid-column: 1 / -1; box-shadow: 0 4px 6px rgba(0,0,0,0.05); }
        .btn { background: #007bff; color: white; border: none; padding: 8px 12px; border-radius: 4px; cursor: pointer; font-weight: bold; font-size: 13px; text-decoration: none; display: inline-block; margin-top: 10px; }
        .btn:hover { background: #0056b3; }
        .btn-reload { background: #6c757d; float: right; }
    </style>
</head>
<body>
    <div>
        <h2>Panel de Control Kiosqly (Render / Servidor)</h2>
        <a href="/" class="btn btn-reload">🔄 Refrescar Panel</a>
    </div>
    <div style="clear: both; margin-height: 20px;"></div>
    <div class="grid">
        {% for device_id, info in devices.items() %}
        <div class="card">
            <h3>{{ info.get('device_name', device_id) }}</h3>
            <div class="info-group">
                <label>ID del Dispositivo:</label> {{ device_id }}
            </div>
            <div class="info-group">
                <label>Batería:</label> {{ info.get('battery', 'N/D') }}%
            </div>
            <div class="info-group">
                <label>URL Actual:</label> 
                <a href="{{ info.get('current_url', '#') }}" target="_blank">{{ info.get('current_url', 'N/D') }}</a>
            </div>
        </div>
        {% else %}
        <div class="empty-state">
            <h3>No hay dispositivos conectados actualmente.</h3>
            <p>Esperando peticiones POST en <code>/heartbeat</code> desde las tabletas Android...</p>
        </div>
        {% endfor %}
    </div>
</body>
</html>
"""

@app.route('/')
def index():
    # Renderiza la plantilla directamente inyectando el diccionario de dispositivos
    return render_template_string(HTML_TEMPLATE, devices=devices_db)

@app.route('/heartbeat', methods=['POST'])
def heartbeat():
    data = request.json or request.form
    device_id = data.get('device_id')
    
    if not device_id:
        return jsonify({'status': 'error', 'message': 'device_id missing'}), 400

    if device_id not in devices_db:
        devices_db[device_id] = {
            'target_url': None,
            'should_reload': False,
            'capture_image': False,
            'last_image': None
        }

    # Actualizar métricas enviadas por la tableta
    devices_db[device_id]['device_name'] = data.get('device_name', 'Tableta Desconocida')
    devices_db[device_id]['battery'] = data.get('battery', 0)
    devices_db[device_id]['current_url'] = data.get('current_url', 'N/A')
    
    response_data = {'status': 'ok'}
    
    if devices_db[device_id].get('should_reload'):
        response_data['reload_page'] = True
        devices_db[device_id]['should_reload'] = False

    if devices_db[device_id].get('target_url'):
        response_data['url'] = devices_db[device_id]['target_url']
        devices_db[device_id]['target_url'] = None

    return jsonify(response_data), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
