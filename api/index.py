from flask import Flask, render_template_string, request, jsonify
from datetime import datetime

app = Flask(__name__)

devices_db = {}

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Kiosqly Admin Dashboard</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; background: #f4f4f9; color: #333; }
        h1 { color: #2c3e50; }
        table { width: 100%; border-collapse: collapse; margin-top: 20px; background: #fff; box-shadow: 0 2px 5px rgba(0,0,0,0.1); }
        th, td { padding: 12px 15px; text-align: left; border-bottom: 1px solid #ddd; }
        th { background-color: #2c3e50; color: white; }
        tr:hover { background-color: #f1f1f1; }
        .status-online { color: green; font-weight: bold; }
        .no-data { text-align: center; padding: 20px; color: #777; }
    </style>
</head>
<body>
    <h1>Panel de Administración - Kiosqly</h1>
    <p>Dispositivos de quiosco registrados y su estado actual:</p>
    
    <table>
        <thead>
            <tr>
                <th>Device ID</th>
                <th>Última Conexión</th>
                <th>URL Destino</th>
                <th>Estado</th>
            </tr>
        </thead>
        <tbody id="device-table-body">
            <tr><td colspan="4" class="no-data">Cargando dispositivos...</td></tr>
        </tbody>
    </table>

    <script>
        async function fetchDevices() {
            try {
                const response = await fetch('/devices');
                const data = await response.json();
                const tbody = document.getElementById('device-table-body');
                tbody.innerHTML = '';
                
                if (Object.keys(data).length === 0) {
                    tbody.innerHTML = '<tr><td colspan="4" class="no-data">No hay dispositivos conectados</td></tr>';
                    return;
                }

                for (const [id, info] of Object.entries(data)) {
                    const row = document.createElement('tr');
                    row.innerHTML = `
                        <td>${id}</td>
                        <td>${info.last_seen || 'N/A'}</td>
                        <td>${info.target_url || 'N/A'}</td>
                        <td class="status-online">Conectado</td>
                    `;
                    tbody.appendChild(row);
                }
            } catch (error) {
                console.error('Error al obtener los dispositivos:', error);
            }
        }

        fetchDevices();
        setInterval(fetchDevices, 5000);
    </script>
</body>
</html>
"""

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/devices', methods=['GET'])
def get_devices():
    return jsonify(devices_db)

@app.route('/heartbeat', methods=['POST'])
def heartbeat():
    data = request.json
    if not data or 'device_id' not in data:
        return jsonify({"error": "Falta device_id"}), 400
    
    device_id = data['device_id']
    devices_db[device_id] = {
        "last_seen": datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S'),
        "target_url": data.get('target_url', 'N/A')
    }
    
    return jsonify({"status": "success", "message": "Heartbeat registrado"})
