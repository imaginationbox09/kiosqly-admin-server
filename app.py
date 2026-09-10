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
    <title>Control Panel Kiosqly Enterprise</title>
    <style>
        :root {
            --bg-color: #0f172a;
            --card-bg: #1e293b;
            --text-color: #f8fafc;
            --text-muted: #94a3b8;
            --border-color: #334155;
            --primary: #3b82f6;
            --primary-hover: #2563eb;
        }
        [data-theme="light"] {
            --bg-color: #f1f5f9;
            --card-bg: #ffffff;
            --text-color: #0f172a;
            --text-muted: #64748b;
            --border-color: #cbd5e1;
        }
        body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background: var(--bg-color); color: var(--text-color); padding: 20px; margin: 0; transition: background 0.3s, color 0.3s; }
        .navbar { background: var(--card-bg); border: 1px solid var(--border-color); padding: 15px 25px; border-radius: 12px; display: flex; justify-content: space-between; align-items: center; margin-bottom: 25px; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1); }
        .navbar h2 { margin: 0; font-size: 20px; display: flex; align-items: center; gap: 10px; color: var(--primary); }
        .controls { display: flex; align-items: center; gap: 15px; }
        .theme-toggle { background: none; border: 1px solid var(--border-color); color: var(--text-color); cursor: pointer; font-size: 16px; padding: 6px 12px; border-radius: 20px; transition: 0.2s; }
        .theme-toggle:hover { background: var(--border-color); }
        .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(320px, 1fr)); gap: 20px; }
        .card { background: var(--card-bg); border: 1px solid var(--border-color); border-radius: 12px; padding: 20px; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1); border-top: 4px solid var(--primary); }
        .card h3 { margin: 0 0 15px 0; color: var(--primary); font-size: 18px; }
        .info-group { margin-bottom: 12px; font-size: 14px; }
        .info-group label { font-weight: bold; color: var(--text-muted); display: block; margin-bottom: 2px; }
        .info-group a { color: var(--primary); text-decoration: none; word-break: break-all; }
        .info-group a:hover { text-decoration: underline; }
        .empty-state { background: var(--card-bg); border: 1px solid var(--border-color); padding: 40px; text-align: center; border-radius: 12px; color: var(--text-muted); grid-column: 1 / -1; }
        .error-banner { background: #fee2e2; color: #991b1b; padding: 15px; border-radius: 8px; text-align: center; margin-bottom: 20px; font-weight: bold; display: none; border: 1px solid #fecaca; }
        .btn { background: var(--primary); color: white; border: none; padding: 8px 14px; border-radius: 6px; cursor: pointer; font-weight: bold; font-size: 13px; text-decoration: none; display: inline-block; transition: background 0.2s; }
        .btn:hover { background: var(--primary-hover); }
    </style>
</head>
<body data-theme="dark">

    <div class="navbar">
        <h2>📱 Control Panel Kiosqly Enterprise</h2>
        <div class="controls">
            <button class="theme-toggle" onclick="toggleTheme()" title="Cambiar Tema">🌓</button>
            <button class="btn" onclick="loadDevices()">🔄 Actualizar</button>
        </div>
    </div>

    <div id="errorBanner" class="error-banner">⚠️ Error al cargar los dispositivos del servidor. Comprueba la ruta de la API.</div>

    <div class="grid" id="devicesGrid">
        <div class="empty-state">Cargando dispositivos...</div>
    </div>

    <script>
        function toggleTheme() {
            const body = document.body;
            const currentTheme = body.getAttribute('data-theme');
            body.setAttribute('data-theme', currentTheme === 'dark' ? 'light' : 'dark');
        }

        async function loadDevices() {
            const grid = document.getElementById('devicesGrid');
            const errorBanner = document.getElementById('errorBanner');

            try {
                const response = await fetch('/devices');
                if (!response.ok) throw new Error('Error en la respuesta del servidor');
                
                const devices = await response.json();
                errorBanner.style.display = 'none';

                if (devices.length === 0) {
                    grid.innerHTML = `
                        <div class="empty-state">
                            <h3>No hay dispositivos conectados actualmente.</h3>
                            <p>Esperando peticiones POST en <code>/heartbeat</code> desde las tabletas Android...</p>
                        </div>
                    `;
                    return;
                }

                grid.innerHTML = devices.map(dev => `
                    <div class="card">
                        <h3>${dev.deviceName || dev.device_name || dev.id}</h3>
                        <div class="info-group">
                            <label>ID del Dispositivo:</label> ${dev.id}
                        </div>
                        <div class="info-group">
                            <label>Batería:</label> ${dev.battery !== undefined ? dev.battery + '%' : 'N/D'}
                        </div>
                        <div class="info-group">
                            <label>URL Actual:</label> 
                            <a href="${dev.current_url || '#'}" target="_blank">${dev.current_url || 'N/D'}</a>
                        </div>
                    </div>
                `).join('');

            } catch (error) {
                console.error(error);
                errorBanner.style.display = 'block';
                grid.innerHTML = `<div class="empty-state">No se pudieron cargar los datos.</div>`;
            }
        }

        loadDevices();
        setInterval(loadDevices, 5000);
    </script>
</body>
</html>
"""

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/devices', methods=['GET'])
def get_devices():
    devices_list = []
    for dev_id, info in devices_db.items():
        dev_data = info.copy()
        dev_data['id'] = dev_id
        if 'deviceName' not in dev_data and 'device_name' in dev_data:
            dev_data['deviceName'] = dev_data['device_name']
        devices_list.append(dev_data)
        
    return jsonify(devices_list), 200

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
