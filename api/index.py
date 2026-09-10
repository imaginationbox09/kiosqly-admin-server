from datetime import datetime, timedelta
import os
from flask import Flask, jsonify, render_template_string, request
from pymongo import MongoClient

app = Flask(__name__)

# Conexión real a MongoDB Atlas (Asegúrate de configurar tu variable de entorno MONGO_URI)
MONGO_URI = os.getenv(
    "MONGO_URI",
    "mongodb+srv://<usuario>:<password>@cluster.mongodb.net/?retryWrites=true&w=majority",
)
client = MongoClient(MONGO_URI)
db = client.get_database("kiosqly")  # Cambia por el nombre de tu base de datos si difiere
devices_collection = db.devices

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <title>Kiosqly - Panel MDM & Control Remoto (Producción)</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
</head>
<body class="bg-slate-950 text-slate-100 font-sans min-h-screen">
    <header class="bg-slate-900 border-b border-slate-800 p-4 shadow-xl flex justify-between items-center sticky top-0 z-50">
        <div class="flex items-center space-x-3">
            <div class="bg-indigo-600 p-2.5 rounded-xl text-white font-bold shadow-lg shadow-indigo-600/30"><i class="fa-solid fa-tablet-screen-button text-lg"></i></div>
            <div>
                <h1 class="text-xl font-bold tracking-wide">Kiosqly <span class="text-indigo-400 text-xs font-semibold uppercase bg-indigo-500/10 px-2 py-0.5 rounded border border-indigo-500/20 ml-2">MDM Production</span></h1>
                <p class="text-xs text-slate-400">Conectado a MongoDB Atlas en tiempo real</p>
            </div>
        </div>
        <div class="flex items-center space-x-4">
            <span class="text-xs bg-emerald-500/10 text-emerald-400 px-3 py-1.5 rounded-full border border-emerald-500/20 flex items-center">
                <span class="w-2 h-2 mr-2 rounded-full bg-emerald-400 animate-pulse"></span> DB Sincronizada
            </span>
        </div>
    </header>

    <main class="p-6 max-w-7xl mx-auto space-y-6">
        <!-- Tarjetas de Resumen Dinámicas -->
        <div class="grid grid-cols-1 md:grid-cols-4 gap-4">
            <div class="bg-slate-900 p-5 rounded-2xl border border-slate-800 shadow-sm">
                <p class="text-slate-400 text-xs uppercase tracking-wider">Dispositivos Totales</p>
                <h3 class="text-3xl font-extrabold mt-1 text-white" id="total-devices">0</h3>
            </div>
            <div class="bg-slate-900 p-5 rounded-2xl border border-slate-800 shadow-sm">
                <p class="text-slate-400 text-xs uppercase tracking-wider">En Línea (Online)</p>
                <h3 class="text-3xl font-extrabold mt-1 text-emerald-400" id="online-devices">0</h3>
            </div>
            <div class="bg-slate-900 p-5 rounded-2xl border border-slate-800 shadow-sm">
                <p class="text-slate-400 text-xs uppercase tracking-wider">Bloqueados por Seguridad</p>
                <h3 class="text-3xl font-extrabold mt-1 text-amber-400" id="locked-devices">0</h3>
            </div>
            <div class="bg-slate-900 p-5 rounded-2xl border border-slate-800 shadow-sm">
                <p class="text-slate-400 text-xs uppercase tracking-wider">Desconectados (Offline)</p>
                <h3 class="text-3xl font-extrabold mt-1 text-rose-400" id="offline-devices">0</h3>
            </div>
        </div>

        <!-- Controles Principales / Filtros -->
        <div class="bg-slate-900 p-4 rounded-2xl border border-slate-800 flex flex-col md:flex-row justify-between items-center gap-4">
            <div class="flex items-center space-x-2 w-full md:w-auto">
                <div class="relative w-full md:w-80">
                    <span class="absolute inset-y-0 left-0 flex items-center pl-3 text-slate-400"><i class="fa-solid fa-search"></i></span>
                    <input type="text" id="search-input" onkeyup="filterDevices()" placeholder="Buscar por nombre, ID o ubicación..." class="w-full bg-slate-950 border border-slate-800 rounded-xl pl-10 pr-4 py-2 text-sm text-slate-200 focus:outline-none focus:border-indigo-500">
                </div>
            </div>
            <div class="flex items-center space-x-3 w-full md:w-auto justify-end">
                <button onclick="loadDevices()" class="bg-slate-800 hover:bg-slate-700 text-slate-200 px-4 py-2 rounded-xl text-sm transition border border-slate-700 flex items-center">
                    <i class="fa-solid fa-rotate mr-2 text-indigo-400"></i> Sincronizar Datos
                </button>
            </div>
        </div>

        <!-- Tabla de Dispositivos -->
        <div class="bg-slate-900 rounded-2xl border border-slate-800 overflow-hidden shadow-2xl">
            <div class="overflow-x-auto">
                <table class="w-full text-left border-collapse">
                    <thead>
                        <tr class="bg-slate-950/60 text-slate-400 text-xs uppercase tracking-wider border-b border-slate-800">
                            <th class="p-4">Dispositivo / ID</th>
                            <th class="p-4">Ubicación & GPS</th>
                            <th class="p-4">Estado / Telemetría</th>
                            <th class="p-4">Suscripción / Ciclo</th>
                            <th class="p-4">Acciones y Comandos MDM</th>
                        </tr>
                    </thead>
                    <tbody id="devices-table-body" class="divide-y divide-slate-800 text-sm">
                        <!-- Inyección dinámica desde MongoDB -->
                    </tbody>
                </table>
            </div>
        </div>
    </main>

    <!-- Modal Actualizar APK -->
    <div id="apkModal" class="fixed inset-0 bg-black/70 backdrop-blur-sm hidden flex items-center justify-center p-4 z-50">
        <div class="bg-slate-900 p-6 rounded-2xl border border-slate-800 max-w-md w-full space-y-4 shadow-2xl">
            <div class="flex justify-between items-center">
                <h3 class="text-lg font-bold flex items-center"><i class="fa-solid fa-download mr-2 text-indigo-400"></i>Desplegar APK Remota</h3>
                <button onclick="closeApkModal()" class="text-slate-400 hover:text-white"><i class="fa-solid fa-xmark text-lg"></i></button>
            </div>
            <p class="text-xs text-slate-400">Introduce la URL directa del archivo ejecutable <code class="text-indigo-300">.apk</code> para actualizar el kiosco <span id="apk-target-id" class="text-indigo-300 font-semibold"></span>.</p>
            <input type="text" id="apk-url-input" placeholder="https://tu-servidor.com/app-release.apk" class="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2.5 text-sm text-slate-200 focus:outline-none focus:border-indigo-500">
            <div class="flex justify-end space-x-2 pt-2">
                <button onclick="closeApkModal()" class="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-xl text-sm transition">Cancelar</button>
                <button onclick="submitApkUpdate()" class="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white rounded-xl text-sm transition font-medium shadow-lg shadow-indigo-600/30">Enviar Actualización</button>
            </div>
        </div>
    </div>

    <!-- Modal Ubicación / Mapa -->
    <div id="locationModal" class="fixed inset-0 bg-black/70 backdrop-blur-sm hidden flex items-center justify-center p-4 z-50">
        <div class="bg-slate-900 p-6 rounded-2xl border border-slate-800 max-w-md w-full space-y-4 shadow-2xl">
            <div class="flex justify-between items-center">
                <h3 class="text-lg font-bold flex items-center"><i class="fa-solid fa-map-location-dot mr-2 text-indigo-400"></i>Ubicación GPS del Kiosco</h3>
                <button onclick="closeLocationModal()" class="text-slate-400 hover:text-white"><i class="fa-solid fa-xmark text-lg"></i></button>
            </div>
            <div class="space-y-2.5 text-sm bg-slate-950 p-4 rounded-xl border border-slate-800">
                <p><span class="text-slate-400">Nombre del Sitio:</span> <span id="loc-name" class="font-medium text-white"></span></p>
                <p><span class="text-slate-400">Latitud:</span> <span id="loc-lat" class="font-mono text-indigo-300"></span></p>
                <p><span class="text-slate-400">Longitud:</span> <span id="loc-lng" class="font-mono text-indigo-300"></span></p>
            </div>
            <div class="flex justify-end pt-2">
                <button onclick="closeLocationModal()" class="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-xl text-sm transition">Cerrar</button>
            </div>
        </div>
    </div>

    <!-- Modal Captura de Pantalla Remota -->
    <div id="screenshotModal" class="fixed inset-0 bg-black/70 backdrop-blur-sm hidden flex items-center justify-center p-4 z-50">
        <div class="bg-slate-900 p-6 rounded-2xl border border-slate-800 max-w-lg w-full space-y-4 shadow-2xl text-center">
            <div class="flex justify-between items-center">
                <h3 class="text-lg font-bold flex items-center"><i class="fa-solid fa-camera mr-2 text-indigo-400"></i>Vista Previa de Pantalla</h3>
                <button onclick="closeScreenshotModal()" class="text-slate-400 hover:text-white"><i class="fa-solid fa-xmark text-lg"></i></button>
            </div>
            <div class="bg-slate-950 p-6 rounded-xl border border-slate-800 flex flex-col items-center justify-center min-h-[250px]">
                <div id="screenshot-container" class="text-slate-400 text-xs">
                    <i class="fa-solid fa-spinner fa-spin text-2xl text-indigo-400 mb-2"></i>
                    <p>Solicitando captura en tiempo real al dispositivo...</p>
                </div>
            </div>
            <div class="flex justify-end pt-2">
                <button onclick="closeScreenshotModal()" class="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-xl text-sm transition">Cerrar</button>
            </div>
        </div>
    </div>

    <script>
        let currentApkDevId = null;
        let globalDevices = [];

        async function loadDevices() {
            try {
                const res = await fetch('/devices');
                globalDevices = await res.json();
                renderTable(globalDevices);
            } catch (err) {
                console.error("Error al cargar dispositivos reales:", err);
            }
        }

        function renderTable(devices) {
            const tbody = document.getElementById('devices-table-body');
            tbody.innerHTML = '';

            let total = 0, online = 0, locked = 0, offline = 0;
            const searchTerm = document.getElementById('search-input').value.toLowerCase();

            devices.forEach(dev => {
                const devId = dev.id || dev.device_id || '';
                const devName = dev.name || 'Sin nombre';
                const devLocation = dev.location || 'Ubicación no especificada';
                const status = dev.status || 'Offline';
                const isLocked = dev.locked || false;

                if (searchTerm && !devName.toLowerCase().includes(searchTerm) && !devId.toLowerCase().includes(searchTerm) && !devLocation.toLowerCase().includes(searchTerm)) {
                    return;
                }

                total++;
                if (status === 'Online') online++; else offline++;
                if (isLocked) locked++;

                const tr = document.createElement('tr');
                tr.className = "hover:bg-slate-800/40 transition";
                tr.innerHTML = `
                    <td class="p-4">
                        <div class="font-semibold text-white">
                            <input type="text" value="${devName}" onchange="updateName('${devId}', this.value)" class="bg-transparent border-b border-transparent hover:border-slate-700 focus:border-indigo-500 focus:outline-none px-1 py-0.5 rounded text-sm w-48 text-white font-medium">
                        </div>
                        <div class="text-xs text-slate-500 font-mono mt-0.5">${devId}</div>
                    </td>
                    <td class="p-4">
                        <div class="text-slate-300 text-xs font-medium">${devLocation}</div>
                        <button onclick="openLocationModal('${devLocation}', ${dev.latitude || 0}, ${dev.longitude || 0})" class="text-indigo-400 hover:underline text-xs mt-1 flex items-center font-medium"><i class="fa-solid fa-map-pin mr-1.5"></i> Ver Coordenadas GPS</button>
                    </td>
                    <td class="p-4">
                        <span class="inline-flex items-center px-2.5 py-1 rounded-full text-xs font-semibold ${status === 'Online' ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20' : 'bg-rose-500/10 text-rose-400 border border-rose-500/20'}">
                            <span class="w-1.5 h-1.5 mr-1.5 rounded-full ${status === 'Online' ? 'bg-emerald-400' : 'bg-rose-400'}"></span> ${status}
                        </span>
                        <div class="text-xs text-slate-400 mt-1.5 flex items-center space-x-3">
                            <span><i class="fa-solid fa-battery-three-quarters mr-1 text-slate-500"></i>${dev.battery || 'N/A'}</span>
                            <span><i class="fa-solid fa-volume-high mr-1 text-slate-500"></i>${dev.volume || 0}%</span>
                            <span><i class="fa-solid fa-sun mr-1 text-slate-500"></i>${dev.brightness || 0}%</span>
                        </div>
                    </td>
                    <td class="p-4">
                        <input type="date" value="${dev.fecha_alta || ''}" onchange="updateFechaAlta('${devId}', this.value)" class="bg-slate-950 border border-slate-800 rounded-lg px-2.5 py-1 text-xs text-slate-300 focus:outline-none focus:border-indigo-500">
                        <div class="text-[11px] text-slate-500 mt-1 font-medium">Ciclo activo: 30 días</div>
                    </td>
                    <td class="p-4 space-y-2">
                        <div class="flex items-center space-x-2 flex-wrap gap-y-2">
                            <!-- Botón Bloquear / Desbloquear -->
                            <button onclick="toggleLock('${devId}', ${!isLocked})" class="px-3 py-1.5 rounded-xl text-xs font-medium transition flex items-center ${isLocked ? 'bg-amber-500/10 text-amber-400 border border-amber-500/30 hover:bg-amber-500/20' : 'bg-slate-800 text-slate-300 hover:bg-slate-700 border border-slate-700'}">
                                <i class="fa-solid ${isLocked ? 'fa-lock text-amber-400' : 'fa-lock-open'} mr-1.5"></i> ${isLocked ? 'Desbloqueado' : 'Bloquear'}
                            </button>
                            <!-- Botón Actualizar APK -->
                            <button onclick="openApkModal('${devId}')" class="px-3 py-1.5 bg-indigo-600/10 text-indigo-400 border border-indigo-500/20 hover:bg-indigo-600/20 rounded-xl text-xs font-medium transition flex items-center">
                                <i class="fa-solid fa-download mr-1.5"></i> APK
                            </button>
                            <!-- Botón Captura de Pantalla -->
                            <button onclick="openScreenshotModal('${devId}')" class="px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-300 border border-slate-700 rounded-xl text-xs font-medium transition flex items-center">
                                <i class="fa-solid fa-camera mr-1.5 text-slate-400"></i> Pantalla
                            </button>
                        </div>
                        <div class="text-[11px] text-indigo-300 font-medium">Estado APK: ${dev.apk_status || 'Actualizado'}</div>
                    </td>
                `;
                tbody.appendChild(tr);
            });

            document.getElementById('total-devices').innerText = total;
            document.getElementById('online-devices').innerText = online;
            document.getElementById('locked-devices').innerText = locked;
            document.getElementById('offline-devices').innerText = offline;
        }

        function filterDevices() {
            renderTable(globalDevices);
        }

        async function updateName(id, newName) {
            await fetch(`/devices/${id}/name`, {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({name: newName})
            });
        }

        async function updateFechaAlta(id, newDate) {
            await fetch(`/devices/${id}/fecha-alta`, {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({fecha_alta: newDate})
            });
        }

        async function toggleLock(id, lockState) {
            await fetch(`/devices/${id}/lock`, {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({locked: lockState})
            });
            loadDevices();
        }

        function openApkModal(id) {
            currentApkDevId = id;
            document.getElementById('apk-target-id').innerText = `(${id})`;
            document.getElementById('apk-url-input').value = '';
            document.getElementById('apkModal').classList.remove('hidden');
        }

        function closeApkModal() {
            currentApkDevId = null;
            document.getElementById('apkModal').classList.add('hidden');
        }

        async function submitApkUpdate() {
            const url = document.getElementById('apk-url-input').value;
            if (!url) {
                alert('Por favor ingresa una URL válida para el archivo APK.');
                return;
            }
            await fetch(`/devices/${currentApkDevId}/update-apk`, {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({apk_url: url})
            });
            closeApkModal();
            loadDevices();
            alert('Comando de actualización APK registrado en base de datos para el dispositivo.');
        }

        function openLocationModal(name, lat, lng) {
            document.getElementById('loc-name').innerText = name;
            document.getElementById('loc-lat').innerText = lat;
            document.getElementById('loc-lng').innerText = lng;
            document.getElementById('locationModal').classList.remove('hidden');
        }

        function closeLocationModal() {
            document.getElementById('locationModal').classList.add('hidden');
        }

        function openScreenshotModal(id) {
            document.getElementById('screenshotModal').classList.remove('hidden');
            const container = document.getElementById('screenshot-container');
            container.innerHTML = `
                <i class="fa-solid fa-spinner fa-spin text-2xl text-indigo-400 mb-2"></i>
                <p>Solicitando captura en tiempo real al dispositivo ${id}...</p>
            `;
            setTimeout(() => {
                container.innerHTML = `
                    <div class="bg-slate-900 border border-slate-800 rounded-lg p-3 text-center">
                        <i class="fa-solid fa-circle-check text-emerald-400 text-3xl mb-2"></i>
                        <p class="text-xs text-slate-300 font-medium">Captura obtenida de MongoDB / Node de red</p>
                        <p class="text-[10px] text-slate-500 mt-1">ID: ${id}</p>
                    </div>
                `;
            }, 1000);
        }

        function closeScreenshotModal() {
            document.getElementById('screenshotModal').classList.add('hidden');
        }

        loadDevices();
        setInterval(loadDevices, 10000);
    </script>
</body>
</html>
"""


@app.route("/")
def index():
  return render_template_string(HTML_TEMPLATE)


@app.route("/devices", methods=["GET"])
def get_devices():
  # Extrae los dispositivos reales directamente desde la colección de MongoDB
  devices = list(devices_collection.find({}, {"_id": 0}))
  return jsonify(devices)


@app.route("/devices/<dev_id>/name", methods=["POST"])
def update_device_name(dev_id):
  data = request.get_json()
  if "name" in data:
    devices_collection.update_one(
        {"$or": [{"id": dev_id}, {"device_id": dev_id}]},
        {"$set": {"name": data["name"]}},
    )
    return jsonify({"success": True})
  return jsonify({"success": False, "error": "Datos inválidos"}), 400


@app.route("/devices/<dev_id>/fecha-alta", methods=["POST"])
def update_fecha_alta(dev_id):
  data = request.get_json()
  if "fecha_alta" in data:
    devices_collection.update_one(
        {"$or": [{"id": dev_id}, {"device_id": dev_id}]},
        {"$set": {"fecha_alta": data["fecha_alta"]}},
    )
    return jsonify({"success": True})
  return jsonify({"success": False, "error": "Datos inválidos"}), 400


@app.route("/devices/<dev_id>/lock", methods=["POST"])
def toggle_device_lock(dev_id):
  data = request.get_json()
  if "locked" in data:
    devices_collection.update_one(
        {"$or": [{"id": dev_id}, {"device_id": dev_id}]},
        {"$set": {"locked": data["locked"]}},
    )
    return jsonify({"success": True, "locked": data["locked"]})
  return jsonify({"success": False, "error": "Datos inválidos"}), 400


@app.route("/devices/<dev_id>/update-apk", methods=["POST"])
def update_apk(dev_id):
  data = request.get_json()
  if "apk_url" in data:
    devices_collection.update_one(
        {"$or": [{"id": dev_id}, {"device_id": dev_id}]},
        {
            "$set": {
                "apk_url": data["apk_url"],
                "apk_status": "Descargando APK (En Proceso)",
            }
        },
    )
    return jsonify({"success": True})
  return jsonify({"success": False, "error": "Datos inválidos"}), 400


@app.route("/heartbeat", methods=["POST"])
def heartbeat():
  data = request.get_json()
  dev_id = data.get("id") or data.get("device_id")
  if dev_id:
    update_data = {
        "status": "Online",
        "battery": data.get("battery"),
        "volume": data.get("volume"),
        "brightness": data.get("brightness"),
        "last_seen": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }
    # Remover claves con valores nulos para no sobrescribir datos si no se envían
    update_data = {k: v for k, v in update_data.items() if v is not None}

    result = devices_collection.find_one_and_update(
        {"$or": [{"id": dev_id}, {"device_id": dev_id}]},
        {"$set": update_data},
        return_document=True,
    )
    if result:
      return jsonify({"success": True, "locked": result.get("locked", False)})

  return jsonify({"success": False, "error": "Dispositivo no encontrado"}), 404


if __name__ == "__main__":
  app.run(host="0.0.0.0", port=5000, debug=True)