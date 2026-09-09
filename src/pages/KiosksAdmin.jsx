import React, { useState, useEffect, useMemo } from 'react';

export default function KiosksAdmin() {
  const [devices, setDevices] = useState([]);
  const [selectedTenant, setSelectedTenant] = useState('TODOS');
  const [searchQuery, setSearchQuery] = useState('');
  const [toast, setToast] = useState('');
  const [busyByDevice, setBusyByDevice] = useState({});
  const [wallpaperByDevice, setWallpaperByDevice] = useState({});
  const [aliasByDevice, setAliasByDevice] = useState({});
  const [apkByDevice, setApkByDevice] = useState({});
  const [expandedBusinesses, setExpandedBusinesses] = useState({});

  // Cargar dispositivos desde el backend de Flask / MongoDB
  const fetchDevices = async () => {
    try {
      const res = await fetch('/api/v1/kiosks');
      if (res.ok) {
        const data = await res.json();
        setDevices(Array.isArray(data) ? data : data.data || []);
      }
    } catch (err) {
      console.error("Error al obtener tabletas:", err);
    }
  };

  useEffect(() => {
    fetchDevices();
    const interval = window.setInterval(fetchDevices, 10000);
    return () => window.clearInterval(interval);
  }, []);

  // Extraer lista única de negocios (tenants)
  const tenants = useMemo(() => {
    const list = devices.map(d => d.tenant || d.businessName || 'Sin Asignar');
    return ['TODOS', ...new Set(list)];
  }, [devices]);

  // Agrupar dispositivos por negocio
  const groupedByBusiness = useMemo(() => {
    const groups = {};
    devices.forEach(device => {
      const businessName = device.tenant || device.businessName || 'Sin Asignar';
      if (!groups[businessName]) {
        groups[businessName] = [];
      }
      groups[businessName].push(device);
    });
    
    // Ordenar cada grupo por último ping y contar online
    Object.keys(groups).forEach(business => {
      groups[business].sort((a, b) => new Date(b.lastPing) - new Date(a.lastPing));
    });
    
    return groups;
  }, [devices]);

  // Filtrar dispositivos por negocio y búsqueda, manteniendo la agrupación
  const filteredGroupedDevices = useMemo(() => {
    const filtered = {};
    
    Object.entries(groupedByBusiness).forEach(([businessName, deviceList]) => {
      const matchesTenant = selectedTenant === 'TODOS' || businessName === selectedTenant;
      
      if (matchesTenant) {
        const filteredList = deviceList.filter(device => {
          const matchesSearch = (device.deviceId || '').toLowerCase().includes(searchQuery.toLowerCase()) ||
                        (device.alias || '').toLowerCase().includes(searchQuery.toLowerCase()) ||
                        (device.name || '').toLowerCase().includes(searchQuery.toLowerCase()) ||
                        (device.location || '').toLowerCase().includes(searchQuery.toLowerCase());
          return matchesSearch;
        });
        
        if (filteredList.length > 0) {
          filtered[businessName] = filteredList;
        }
      }
    });
    
    return filtered;
  }, [groupedByBusiness, selectedTenant, searchQuery]);

  // Contar dispositivos online por negocio
  const countOnlineByBusiness = useMemo(() => {
    const counts = {};
    Object.entries(groupedByBusiness).forEach(([businessName, deviceList]) => {
      counts[businessName] = deviceList.filter(d => d.status === 'ONLINE').length;
    });
    return counts;
  }, [groupedByBusiness]);

  // Enviar comando remoto
  const sendCommand = async (deviceId, command, payload = {}) => {
    setBusyByDevice(curr => ({ ...curr, [deviceId]: true }));
    try {
      const res = await fetch(`/api/v1/kiosks/${deviceId}/command`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ deviceId, command, ...payload })
      });
      if (res.ok) {
        setToast(`Comando '${command}' enviado a ${deviceId}`);
      } else {
        setToast(`Error al enviar comando`);
      }
    } catch (e) {
      setToast(`Fallo de red al enviar comando`);
    } finally {
      setBusyByDevice(curr => ({ ...curr, [deviceId]: false }));
      setTimeout(() => setToast(''), 3500);
    }
  };

  return (
    <div className="p-6 max-w-7xl mx-auto min-h-screen bg-gray-50">
      {/* Notificación flotante (Toast) */}
      {toast && (
        <div className="fixed top-5 right-5 z-50 bg-gray-900 text-white px-4 py-2 rounded-lg shadow-lg text-sm">
          {toast}
        </div>
      )}

      {/* Cabecera del Panel */}
      <div className="bg-white border rounded-xl p-6 shadow-sm mb-6 flex flex-col md:flex-row justify-between items-center gap-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Kiosqly Control Panel Pro 🚀</h1>
          <p className="text-sm text-gray-500">Gestión centralizada, ubicación y segmentación por negocio</p>
        </div>

        {/* Filtros de Negocio y Búsqueda */}
        <div className="flex flex-wrap items-center gap-3">
          <select 
            value={selectedTenant}
            onChange={(e) => setSelectedTenant(e.target.value)}
            className="px-4 py-2 border rounded-lg bg-white text-sm font-medium text-gray-700 shadow-sm"
          >
            {tenants.map(t => (
              <option key={t} value={t}>Negocio: {t}</option>
            ))}
          </select>

          <input 
            type="text" 
            placeholder="Buscar por ID o Ubicación..." 
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="px-4 py-2 border rounded-lg text-sm bg-white shadow-sm w-60"
          />

          <button 
            onClick={fetchDevices}
            className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg text-sm font-medium shadow-sm transition"
          >
            Refrescar
          </button>
        </div>
      </div>

      {/* Grid de Dispositivos Agrupados por Negocio */}
      <div className="space-y-4">
        {Object.entries(filteredGroupedDevices).length === 0 ? (
          <div className="text-center py-16 text-gray-400 bg-white rounded-xl border">
            No hay tabletas registradas o que coincidan con el filtro seleccionado.
          </div>
        ) : (
          Object.entries(filteredGroupedDevices).map(([businessName, deviceList]) => {
            const isExpanded = expandedBusinesses[businessName] !== false; // Expandido por defecto
            const onlineCount = countOnlineByBusiness[businessName] || 0;
            const totalCount = deviceList.length;
            const businessColor = businessName === 'Sin Asignar' ? 'gray' : 'indigo';

            return (
              <div key={businessName} className="bg-white border rounded-xl shadow-sm overflow-hidden">
                {/* Encabezado del Acordeón */}
                <button
                  onClick={() => setExpandedBusinesses(curr => ({ ...curr, [businessName]: !curr[businessName] }))}
                  className={`w-full px-6 py-4 flex items-center justify-between font-semibold text-lg border-b transition hover:bg-gray-50 ${
                    businessColor === 'indigo' ? 'text-indigo-900' : 'text-gray-900'
                  }`}
                >
                  <div className="flex items-center gap-3">
                    <span className={`text-2xl ${businessColor === 'indigo' ? 'text-indigo-600' : 'text-gray-600'}`}>
                      {businessName === 'Sin Asignar' ? '📭' : '🏢'}
                    </span>
                    <div className="text-left">
                      <p>{businessName}</p>
                      <p className={`text-xs font-normal ${businessColor === 'indigo' ? 'text-indigo-600' : 'text-gray-600'}`}>
                        {onlineCount} en línea de {totalCount} dispositivos
                      </p>
                    </div>
                  </div>
                  <span className={`transform transition-transform text-xl ${isExpanded ? 'rotate-180' : ''}`}>
                    ▼
                  </span>
                </button>

                {/* Contenido del Acordeón */}
                {isExpanded && (
                  <div className="p-6">
                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                      {deviceList.map(device => {
                        const ipAddress = device.localIp || device.ipAddress || device.ip || 'IP no disponible';
                        const isBusy = busyByDevice[device.deviceId];
                        const displayValue = value => value === undefined || value === null || value === '' ? 'N/A' : value;
                        const isOnline = device.status === 'ONLINE';

                        return (
                          <div key={device.deviceId || device._id} className={`bg-white border rounded-xl shadow-sm p-5 flex flex-col justify-between transition ${
                            isOnline ? 'border-green-200 bg-gradient-to-br from-white to-green-50' : 'border-gray-200 opacity-75'
                          }`}>
                            <div>
                              <div className="flex justify-between items-start mb-3">
                                <div className="flex-1">
                                  <div className="flex items-center gap-2 mb-1">
                                    <span className={`text-xs font-bold px-2 py-1 rounded ${
                                      isOnline 
                                        ? 'bg-green-100 text-green-800' 
                                        : 'bg-red-100 text-red-800'
                                    }`}>
                                      {isOnline ? '🟢 En Línea' : '🔴 Desconectado'}
                                    </span>
                                  </div>
                                  <h3 className="text-md font-bold text-gray-800">{device.alias || device.name || 'Tableta sin alias'}</h3>
                                  <p className="text-xs text-gray-500 font-mono">{device.deviceId}</p>
                                </div>
                                <span className="text-xs px-2 py-1 bg-gray-100 text-gray-600 rounded whitespace-nowrap">
                                  v{device.appVersion || '1.0.0'}
                                </span>
                              </div>

                              {/* Ubicación y Estado de Hardware */}
                              <div className="space-y-1.5 text-xs text-gray-600 mb-4 bg-gray-50 p-3 rounded-lg border">
                                <p>📍 <strong>Ubicación:</strong> {device.location || 'No registrada'}</p>
                                <p>🌐 <strong>IP:</strong> {ipAddress}</p>
                                <p>🔋 <strong>Batería:</strong> {device.batteryLevel ?? 'N/A'}% | 📶 <strong>Red:</strong> {device.wifiSignal || 'Wi-Fi'}</p>
                                <p>📶 <strong>Wi-Fi:</strong> {displayValue(device.wifiSsid)}</p>
                                <p>💾 <strong>RAM:</strong> {displayValue(device.ramFreeMb)} / {displayValue(device.ramTotalMb)} MB</p>
                                <p>📦 <strong>Almacenamiento:</strong> {displayValue(device.storageFreeMb)} / {displayValue(device.storageTotalMb)} MB</p>
                                <p>☀️ <strong>Brillo:</strong> {displayValue(device.brightness)} | 🔊 <strong>Volumen:</strong> {displayValue(device.volume)}</p>
                                <p>🛰️ <strong>GPS:</strong> {displayValue(device.gps)}</p>
                              </div>
                            </div>

                            {/* Controles Remotos por Tableta */}
                            <div className="border-t pt-3 flex flex-col gap-2">
                              <div className="grid grid-cols-2 gap-2">
                                <button 
                                  disabled={isBusy}
                                  onClick={() => sendCommand(device.deviceId, 'RELOAD')}
                                  className="bg-amber-500 hover:bg-amber-600 disabled:opacity-50 text-white text-xs py-1.5 px-3 rounded font-medium transition"
                                >
                                  Recargar
                                </button>
                                <button 
                                  disabled={isBusy}
                                  onClick={() => sendCommand(device.deviceId, 'CLEAR_CACHE')}
                                  className="bg-slate-700 hover:bg-slate-800 disabled:opacity-50 text-white text-xs py-1.5 px-3 rounded font-medium transition"
                                >
                                  Limpiar Caché
                                </button>
                              </div>
                              <div className="flex gap-2">
                                <input
                                  type="text"
                                  value={aliasByDevice[device.deviceId] || ''}
                                  onChange={e => setAliasByDevice(curr => ({ ...curr, [device.deviceId]: e.target.value }))}
                                  placeholder="Alias de la tableta"
                                  className="min-w-0 flex-1 border rounded px-2 py-1.5 text-xs"
                                />
                                <button
                                  disabled={isBusy || !aliasByDevice[device.deviceId]}
                                  onClick={() => sendCommand(device.deviceId, 'set_alias', { alias: aliasByDevice[device.deviceId] })}
                                  className="bg-cyan-600 hover:bg-cyan-700 disabled:opacity-50 text-white text-xs py-1.5 px-3 rounded font-medium transition"
                                >
                                  Guardar Alias
                                </button>
                              </div>
                              <div className="flex gap-2">
                                <input
                                  type="url"
                                  value={apkByDevice[device.deviceId] || ''}
                                  onChange={e => setApkByDevice(curr => ({ ...curr, [device.deviceId]: e.target.value }))}
                                  placeholder="URL del nuevo APK"
                                  className="min-w-0 flex-1 border rounded px-2 py-1.5 text-xs"
                                />
                                <button
                                  disabled={isBusy || !apkByDevice[device.deviceId]}
                                  onClick={() => sendCommand(device.deviceId, 'update_app', { url: apkByDevice[device.deviceId] })}
                                  className="bg-emerald-600 hover:bg-emerald-700 disabled:opacity-50 text-white text-xs py-1.5 px-3 rounded font-medium transition"
                                >
                                  Actualizar App
                                </button>
                              </div>
                              <div className="grid grid-cols-3 gap-2">
                                <button disabled={isBusy} onClick={() => sendCommand(device.deviceId, 'RELOAD')} className="bg-amber-500 hover:bg-amber-600 disabled:opacity-50 text-white text-xs py-1.5 px-2 rounded font-medium transition">Refrescar Pantalla</button>
                                <button disabled={isBusy} onClick={() => sendCommand(device.deviceId, 'lock_device')} className="bg-red-600 hover:bg-red-700 disabled:opacity-50 text-white text-xs py-1.5 px-2 rounded font-medium transition">Bloquear</button>
                                <button disabled={isBusy} onClick={() => sendCommand(device.deviceId, 'unlock_device')} className="bg-green-600 hover:bg-green-700 disabled:opacity-50 text-white text-xs py-1.5 px-2 rounded font-medium transition">Desbloquear</button>
                              </div>
                              <div className="flex gap-2">
                                <input
                                  type="url"
                                  value={wallpaperByDevice[device.deviceId] || ''}
                                  onChange={e => setWallpaperByDevice(curr => ({ ...curr, [device.deviceId]: e.target.value }))}
                                  placeholder="URL del wallpaper"
                                  className="min-w-0 flex-1 border rounded px-2 py-1.5 text-xs"
                                />
                                <button
                                  disabled={isBusy || !wallpaperByDevice[device.deviceId]}
                                  onClick={() => sendCommand(device.deviceId, 'set_wallpaper', { url: wallpaperByDevice[device.deviceId] })}
                                  className="bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50 text-white text-xs py-1.5 px-3 rounded font-medium transition"
                                >
                                  Wallpaper
                                </button>
                              </div>
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  </div>
                )}
              </div>
            );
          })
        )}
      </div>
    </div>
  );
}
