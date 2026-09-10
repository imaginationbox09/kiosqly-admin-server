from flask import Flask, render_template_string, request, jsonify
from datetime import datetime

app = Flask(__name__)

# Base de datos en memoria con todas las propiedades avanzadas
devices_db = {
    "418dccd381cd5dd8": {
        "id": "418dccd381cd5dd8",
        "deviceName": "Kiosco Brisas Central",
        "model": "Kiosqly Tab 10",
        "sucursal": "Brisas del Golf - Local 4",
        "ip": "192.168.1.50",
        "ram": "1.8 GB / 4 GB",
        "storage": "32 GB / 64 GB",
        "brillo": "75%",
        "volumen": "80%",
        "target_url": "https://kiosqly.com/menu",
        "online": True,
        "fechaAlta": "2026-08-10",
        "screenshotUrl": "",
        "photoUrl": "",
        "last_seen": datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
    }
}

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="es" data-theme="dark">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Kiosqly Control Panel Enterprise Pro</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <style>
        :root {
            --bg-color: #0f172a;
            --card-bg: #1e293b;
            --text-color: #f8fafc;
            --text-muted: #94a3b8;
            --border-color: #334155;
            --primary: #3b82f6;
            --primary-hover: #2563eb;
            --accent-success: #10b981;
            --accent-warning: #f59e0b;
            --accent-danger: #ef4444;
        }

        [data-theme="light"] {
            --bg-color: #f1f5f9;
            --card-bg: #ffffff;
            --text-color: #0f172a;
            --text-muted: #64748b;
            --border-color: #e2e8f0;
            --primary: #2563eb;
            --primary-hover: #1d4ed8;
            --accent-success: #059669;
            --accent-warning: #d97706;
            --accent-danger: #dc2626;
        }

        * { box-sizing: border-box; margin: 0; padding: 0; font-family: 'Inter', sans-serif; transition: background 0.3s, color 0.3s, border-color 0.3s; }
        body { background-color: var(--bg-color); color: var(--text-color); padding: 20px; }

        header {
            display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 16px;
            margin-bottom: 24px; background: var(--card-bg); padding: 16px 24px;
            border-radius: 12px; border: 1px solid var(--border-color);
        }
        .logo-area { display: flex; align-items: center; gap: 12px; font-size: 1.25rem; font-weight: 700; }
        
        .controls-header { display: flex; align-items: center; gap: 16px; }
        .theme-switch {
            background: var(--border-color); border: none; cursor: pointer;
            width: 48px; height: 24px; border-radius: 12px; position: relative;
            display: flex; align-items: center; padding: 2px;
        }
        .theme-switch .ball {
            width: 20px; height: 20px; background: white; border-radius: 50%;
            transition: transform 0.3s; transform: translateX(0);
        }
        [data-theme="light"] .theme-switch .ball { transform: translateX(24px); }

        .toolbar {
            display: flex; gap: 12px; margin-bottom: 20px; flex-wrap: wrap; align-items: center;
        }
        .search-input, .filter-select {
            background: var(--card-bg); color: var(--text-color); border: 1px solid var(--border-color);
            padding: 8px 14px; border-radius: 8px; font-size: 0.9rem; outline: none;
        }
        .search-input { flex: 1; min-width: 240px; }

        .grid-devices {
            display: grid; grid-template-columns: repeat(auto-fill, minmax(350px, 1fr)); gap: 20px;
        }
        .device-card {
            background: var(--card-bg); border: 1px solid var(--border-color);
            border-radius: 12px; padding: 20px; position: relative;
        }
        .device-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; }
        
        .device-name-area { display: flex; align-items: center; gap: 8px; font-size: 1.1rem; font-weight: 600; color: var(--primary); }
        .device-name-input {
            background: var(--bg-color); color: var(--text-color); border: 1px solid var(--primary);
            padding: 2px 6px; border-radius: 4px; font-size: 1rem; font-weight: 600; display: none; width: 180px;
        }
        .edit-btn { background: none; border: none; color: var(--text-muted); cursor: pointer; font-size: 0.9rem; }
        .edit-btn:hover { color: var(--primary); }

        .info-group { margin-bottom: 8px; font-size: 0.9rem; color: var(--text-muted); display: flex; align-items: center; justify-content: space-between; }
        .info-group strong { color: var(--text-color); }

        .metrics-row {
            display: grid; grid-template-columns: 1fr 1fr; gap: 8px; margin: 12px 0;
            background: rgba(0,0,0,0.05); padding: 10px; border-radius: 8px; border: 1px solid var(--border-color);
        }
        [data-theme="dark"] .metrics-row { background: rgba(255,255,255,0.03); }

        .metric-item { font-size: 0.82rem; color: var(--text-muted); }
        .metric-item span { display: block; font-weight: 600; color: var(--text-color); font-size: 0.95rem; }
        .metric-item a { display: block; font-weight: 600; color: var(--primary); font-size: 0.9rem; text-decoration: none; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
        .metric-item a:hover { text-decoration: underline; }

        .action-url-box {
            margin-top: 10px; display: flex; gap: 6px; align-items: center;
        }
        .action-url-box select {
            flex: 1; background: var(--bg-color); color: var(--text-color); border: 1px solid var(--border-color);
            padding: 6px; border-radius: 6px; font-size: 0.82rem;
        }

        .subscription-box {
            background: rgba(59, 130, 246, 0.08); border: 1px solid var(--border-color);
            padding: 10px; border-radius: 8px; margin-top: 12px; font-size: 0.85rem;
        }
        .countdown { font-weight: 700; color: var(--accent-warning); }

        .btn-action {
            background: var(--primary); color: white; border: none; padding: 8px 12px;
            border-radius: 6px; cursor: pointer; font-size: 0.85rem; font-weight: 500;
            display: inline-flex; align-items: center; gap: 6px; margin-top: 8px;
        }
        .btn-action:hover { background: var(--primary-hover); }

        .modal {
            display: none; position: fixed; top: 0; left: 0; width: 100%; height: 100%;
            background: rgba(0,0,0,0.75); justify-content: center; align-items: center; z-index: 1000;
        }
        .modal-content {
            background: var(--card-bg); padding: 20px; border-radius: 12px; max-width: 650px; width: 90%;
            text-align: center; border: 1px solid var(--border-color);
        }
        .modal-content img { max-width: 100%; max-height: 70vh; height: auto; border-radius: 8px; margin-top: 12px; border: 1px solid var(--border-color); object-fit: contain; }
    </style>
</head>
<body>

    <header>
        <div class="logo-area">
            <i class="fa-solid fa-tablet-screen-button" style="color: var(--primary);"></i> Control Panel Kiosqly Enterprise Pro
        </div>
        <div class="controls-header">
            <span id="theme-label"><i class="fa-solid fa-moon"></i></span>
            <button class="theme-switch" onclick="toggleTheme()" id="themeBtn" title="Cambiar Modo Claro/Oscuro">
                <div class="ball"></div>
            </button>
        </div>
    </header>

    <div class="toolbar">
        <div style="position: relative; flex: 1;">
            <i class="fa-solid fa-magnifying-glass" style="position: absolute; left: 12px; top: 11px; color: var(--text-muted);"></i>
            <input type="text" id="searchInput" class="search-input" placeholder="Buscar por nombre, sucursal o IP..." oninput="filtrarDispositivos()" style="padding-left: 36px; width: 100%;">
        </div>
        <select id="filterStatus" class="filter-select" onchange="filtrarDispositivos()">
            <option value="all">Todos los estados</option>
            <option value="online">Online</option>
            <option value="offline">Offline</option>
        </select>
    </div>

    <div class="grid-devices" id="deviceGrid">
        <div style="color: var(--text-muted); padding: 20px; grid-column: 1 / -1; text-align: center;">
            <i class="fa-solid fa-spinner fa-spin"></i> Cargando dispositivos...
        </div>
    </div>

    <div class="modal" id="mediaModal" onclick="cerrarModalFuera(event)">
        <div class="modal-content">
            <h3 id="modalTitle" style="color: var(--text-color);">Vista Remota</h3>
            <div id="modalBody">
                <img id="modalImage" src="" alt="Multimedia de la Tableta">
            </div>
            <br>
            <button class="btn-action" style="background: var(--accent-danger); margin-top: 10px;" onclick="cerrarModal()">Cerrar</button>
        </div>
    </div>

    <script>
        let globalDevicesData = [];

        function toggleTheme() {
            const html = document.documentElement;
            const currentTheme = html.getAttribute('data-theme');
            const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
            html.setAttribute('data-theme', newTheme);
            localStorage.setItem('kiosqly_theme', newTheme);
            
            const icon = document.querySelector('#theme-label i');
            icon.className = newTheme === 'dark' ? 'fa-solid fa-moon' : 'fa-solid fa-sun';
        }

        const savedTheme = localStorage.getItem('kiosqly_theme') || 'dark';
        document.documentElement.setAttribute('data-theme', savedTheme);
        document.querySelector('#theme-label i').className = savedTheme === 'dark' ? 'fa-solid fa-moon' : 'fa-solid fa-sun';

        function cargarDispositivos() {
            fetch('/devices') 
                .then(response => {
                    if (!response.ok) throw new Error("Error al obtener los dispositivos");
                    return response.json();
                })
                .then(devicesData => {
                    globalDevicesData = Array.isArray(devicesData) ? devicesData : Object.values(devicesData);
                    filtrarDispositivos();
                })
                .catch(error => {
                    console.error("Error de conexión:", error);
                    document.getElementById('deviceGrid').innerHTML = `
                        <div style="color: var(--accent-danger); padding: 20px; grid-column: 1 / -1; text-align: center;">
                            <i class="fa-solid fa-triangle-exclamation"></i> Error al cargar los dispositivos del servidor.
                        </div>
                    `;
                });
        }

        function filtrarDispositivos() {
            const query = document.getElementById('searchInput').value.toLowerCase();
            const statusFilter = document.getElementById('filterStatus').value;

            const filtered = globalDevicesData.filter(dev => {
                const name = (dev.deviceName || dev.model || dev.id || '').toLowerCase();
                const sucursal = (dev.sucursal || '').toLowerCase();
                const ip = (dev.ip || '').toLowerCase();
                
                const matchesQuery = name.includes(query) || sucursal.includes(query) || ip.includes(query);
                
                const isOnline = dev.online !== false;
                let matchesStatus = true;
                if (statusFilter === 'online') matchesStatus = isOnline;
                if (statusFilter === 'offline') matchesStatus = !isOnline;

                return matchesQuery && matchesStatus;
            });

            renderizarDispositivos(filtered);
        }

        function renderizarDispositivos(devicesArray) {
            const grid = document.getElementById('deviceGrid');
            grid.innerHTML = '';

            if (devicesArray.length === 0) {
                grid.innerHTML = '<div style="color: var(--text-muted); padding: 20px; grid-column: 1 / -1; text-align: center;">No se encontraron dispositivos con esos filtros.</div>';
                return;
            }

            devicesArray.forEach(dev => {
                let diasRestantesText = "Sin fecha de alta";
                let colorSuscripcion = "var(--text-muted)";
                
                if (dev.fechaAlta) {
                    const fechaAlta = new Date(dev.fechaAlta);
                    const hoy = new Date();
                    const vencimiento = new Date(fechaAlta);
                    vencimiento.setDate(vencimiento.getDate() + 30);
                    
                    const diffTime = vencimiento.getTime() - hoy.getTime();
                    const dias = Math.ceil(diffTime / (1000 * 3600 * 24));
                    
                    if (dias > 5) {
                        colorSuscripcion = "var(--accent-warning)";
                        diasRestantesText = `${dias} días restantes`;
                    } else if (dias >= 0) {
                        colorSuscripcion = "var(--accent-danger)";
                        diasRestantesText = `¡Quedan ${dias} días! (Por vencer)`;
                    } else {
                        colorSuscripcion = "var(--accent-danger)";
                        diasRestantesText = `¡Suscripción Vencida (hace ${Math.abs(dias)} días)!`;
                    }
                }

                const targetUrl = dev.target_url || dev.url || 'N/D';
                const deviceId = dev.id || dev._id;
                const displayName = dev.deviceName || dev.model || deviceId;

                const card = document.createElement('div');
                card.className = 'device-card';
                card.innerHTML = `
                    <div class="device-header">
                        <div class="device-name-area">
                            <i class="fa-solid fa-tablet"></i>
                            <span id="name-text-${deviceId}" style="font-weight: 600; color: var(--primary);">${displayName}</span>
                            <input type="text" id="name-input-${deviceId}" class="device-name-input" value="${displayName}">
                            <button class="edit-btn" id="edit-btn-${deviceId}" onclick="activarEdicion('${deviceId}')" title="Modificar nombre del equipo"><i class="fa-solid fa-pen"></i></button>
                            <button class="edit-btn" id="save-btn-${deviceId}" onclick="guardarNombre('${deviceId}')" style="display:none; color: var(--accent-success);" title="Guardar nombre"><i class="fa-solid fa-check"></i></button>
                        </div>
                        <span style="color: ${dev.online !== false ? 'var(--accent-success)' : 'var(--accent-danger)'}; font-size: 0.85rem; display: flex; align-items: center; gap: 4px;">
                            <i class="fa-solid fa-circle" style="font-size: 8px;"></i> ${dev.online !== false ? 'Online' : 'Offline'}
                        </span>
                    </div>

                    <div class="info-group"><i class="fa-solid fa-location-dot"></i> <span><strong>Sucursal:</strong> ${dev.sucursal || 'Ubicación no registrada'}</span></div>
                    <div class="info-group"><i class="fa-solid fa-network-wired"></i> <span><strong>IP Local:</strong> ${dev.ip || 'N/D'}</span></div>

                    <div class="metrics-row">
                        <div class="metric-item">RAM Libre<span>${dev.ram || 'N/D'}</span></div>
                        <div class="metric-item">Almacenamiento<span>${dev.storage || 'N/D'}</span></div>
                    </div>

                    <div class="metrics-row" style="grid-template-columns: 1fr 1fr 1.5fr;">
                        <div class="metric-item">Brillo<span>${dev.brillo || '50%'}</span></div>
                        <div class="metric-item">Volumen<span>${dev.volumen || '100%'}</span></div>
                        <div class="metric-item">URL Active<a href="${targetUrl !== 'N/D' ? targetUrl : '#'}" target="_blank">${targetUrl}</a></div>
                    </div>

                    <div class="action-url-box">
                        <select id="select-url-${deviceId}">
                            <option value="https://kiosqly.com/menu">Menú Principal Kiosqly</option>
                            <option value="https://kiosqly.com/checkout">Pasarela de Pago</option>
                            <option value="https://google.com">Google (Navegación)</option>
                        </select>
                        <button class="btn-action" style="margin-top: 0; padding: 6px 10px;" onclick="enviarComandoUrl('${deviceId}')"><i class="fa-solid fa-paper-plane"></i></button>
                    </div>

                    <div class="info-group" style="margin-top: 14px; border-top: 1px solid var(--border-color); padding-top: 10px;">
                        <label><strong>Fecha de Alta:</strong></label>
                        <input type="date" value="${dev.fechaAlta || ''}" onchange="actualizarFechaAlta('${deviceId}', this.value)" style="background: var(--bg-color); color: var(--text-color); border: 1px solid var(--border-color); padding: 4px 8px; border-radius: 4px; font-size: 0.85rem;">
                    </div>

                    <div class="subscription-box">
                        <div>Ciclo de Suscripción: <strong>30 Días</strong></div>
                        <div>Estado: <span class="countdown" style="color: ${colorSuscripcion};">${diasRestantesText}</span></div>
                    </div>

                    <div style="margin-top: 15px; display: flex; gap: 8px; flex-wrap: wrap;">
                        <button class="btn-action" onclick="abrirModalMedia('captura', '${dev.screenshotUrl || ''}')">
                            <i class="fa-solid fa-desktop"></i> Ver Pantalla
                        </button>
                        <button class="btn-action" onclick="abrirModalMedia('foto', '${dev.photoUrl || ''}')">
                            <i class="fa-solid fa-camera"></i> Ver Foto HD
                        </button>
                    </div>
                `;
                grid.appendChild(card);
            });
        }

        function activarEdicion(id) {
            document.getElementById(`name-text-${id}`).style.display = 'none';
            document.getElementById(`name-input-${id}`).style.display = 'inline-block';
            document.getElementById(`edit-btn-${id}`).style.display = 'none';
            document.getElementById(`save-btn-${id}`).style.display = 'inline-block';
            document.getElementById(`name-input-${id}`).focus();
        }

        function guardarNombre(id) {
            const nuevoNombre = document.getElementById(`name-input-${id}`).value;
            if (!nuevoNombre.trim()) return;

            fetch(`/devices/${id}/name`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ deviceName: nuevoNombre })
            })
            .then(res => {
                if (!res.ok) throw new Error("No se pudo actualizar el nombre");
                cargarDispositivos();
            })
            .catch(err => console.error("Error al actualizar nombre:", err));
        }

        function actualizarFechaAlta(id, nuevaFecha) {
            fetch(`/devices/${id}/fecha-alta`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ fechaAlta: nuevaFecha })
            })
            .then(res => {
                if (!res.ok) throw new Error("No se pudo guardar la fecha");
                cargarDispositivos();
            })
            .catch(err => console.error("Error al actualizar fecha de alta:", err));
        }

        function enviarComandoUrl(id) {
            const urlSeleccionada = document.getElementById(`select-url-${id}`).value;
            fetch(`/devices/${id}/command`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ target_url: urlSeleccionada })
            })
            .then(res => {
                if (!res.ok) throw new Error("Error al enviar comando");
                alert("¡Comando de navegación enviado al dispositivo!");
                cargarDispositivos();
            })
            .catch(err => alert("No se pudo enviar el comando al equipo."));
        }

        function abrirModalMedia(tipo, url) {
            const modal = document.getElementById('mediaModal');
            const modalTitle = document.getElementById('modalTitle');
            const modalBody = document.getElementById('modalBody');

            modalTitle.innerText = tipo === 'captura' ? 'Vista Remota: Captura de Pantalla' : 'Foto HD de Cámara Remota';
            
            if (!url || url === 'null' || url === 'undefined' || url === "") {
                modalBody.innerHTML = `
                    <div style="padding: 40px; color: var(--text-muted);">
                        <i class="fa-solid fa-triangle-exclamation" style="font-size: 2rem; color: var(--accent-warning); margin-bottom: 10px;"></i>
                        <p>No hay imagen disponible en este momento.</p>
                        <p style="font-size: 0.8rem; margin-top: 5px;">La tableta aún no ha sincronizado la captura o foto reciente.</p>
                    </div>
                `;
            } else {
                modalBody.innerHTML = `<img id="modalImage" src="${url}" alt="Multimedia de Tableta">`;
            }

            modal.style.display = 'flex';
        }

        function cerrarModal() {
            document.getElementById('mediaModal').style.display = 'none';
        }

        function cerrarModalFuera(e) {
            if (e.target.id === 'mediaModal') {
                cerrarModal();
            }
        }

        cargarDispositivos();
        setInterval(cargarDispositivos, 30000);
    </script>
</body>
</html>
"""

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/devices', methods=['GET'])
def get_devices():
    return jsonify(list(devices_db.values()))

@app.route('/devices/<device_id>/name', methods=['POST'])
def update_device_name(device_id):
    data = request.json
    if device_id in devices_db and data and 'deviceName' in data:
        devices_db[device_id]['deviceName'] = data['deviceName']
        return jsonify({"status": "success", "message": "Nombre actualizado con éxito"})
    return jsonify({"error": "Dispositivo no encontrado"}), 404

@app.route('/devices/<device_id>/fecha-alta', methods=['POST'])
def update_fecha_alta(device_id):
    data = request.json
    if device_id in devices_db and data and 'fechaAlta' in data:
        devices_db[device_id]['fechaAlta'] = data['fechaAlta']
        return jsonify({"status": "success", "message": "Fecha de alta actualizada"})
    return jsonify({"error": "Dispositivo no encontrado"}), 404

@app.route('/devices/<device_id>/command', methods=['POST'])
def send_command(device_id):
    data = request.json
    if device_id in devices_db and data and 'target_url' in data:
        devices_db[device_id]['target_url'] = data['target_url']
        return jsonify({"status": "success", "message": "Comando encolado"})
    return jsonify({"error": "Dispositivo no encontrado"}), 404

@app.route('/heartbeat', methods=['POST'])
def heartbeat():
    data = request.json
    if not data or 'device_id' not in data:
        return jsonify({"error": "Falta device_id"}), 400
    
    device_id = data['device_id']
    
    if device_id in devices_db:
        devices_db[device_id]['last_seen'] = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
        devices_db[device_id]['online'] = True
        if 'target_url' in data:
            devices_db[device_id]['target_url'] = data['target_url']
    else:
        devices_db[device_id] = {
            "id": device_id,
            "deviceName": f"Kiosco {device_id[:6]}",
            "model": data.get('model', 'Kiosqly Tablet'),
            "sucursal": data.get('sucursal', 'Sucursal Principal'),
            "ip": data.get('ip', '192.168.1.X'),
            "ram": data.get('ram', '2 GB / 4 GB'),
            "storage": data.get('storage', '30 GB / 64 GB'),
            "brillo": data.get('brillo', '70%'),
            "volumen": data.get('volumen', '90%'),
            "target_url": data.get('target_url', 'https://kiosqly.com/menu'),
            "online": True,
            "fechaAlta": data.get('fechaAlta', ''),
            "screenshotUrl": data.get('screenshotUrl', ''),
            "photoUrl": data.get('photoUrl', ''),
            "last_seen": datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
        }
    
    return jsonify({"status": "success", "message": "Heartbeat registrado", "target_url": devices_db[device_id].get('target_url')})
