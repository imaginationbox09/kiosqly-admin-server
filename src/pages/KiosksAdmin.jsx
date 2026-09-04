import React, { useState, useEffect, useMemo } from 'react';

export default function KiosksAdmin() {
  const [devices, setDevices] = useState([]);
  const [selectedTenant, setSelectedTenant] = useState('TODOS');
  const [searchQuery, setSearchQuery] = useState('');
  const [toast, setToast] = useState('');
  const [busyByDevice, setBusyByDevice] = useState({});

  // Cargar dispositivos desde el backend de Flask / MongoDB
  const fetchDevices = async () => {
    try {
      const res = await fetch('/api/v1/kiosks');
      if (res.ok) {
        const data = await res.json();
        setDevices(data);
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
    const list = devices.map(d => d.tenant || d.businessName || 'General');
    return ['TODOS', ...new Set(list)];
  }, [devices]);

  // Filtrar dispositivos por negocio y búsqueda
  const filteredDevices = useMemo(() => {
    return devices.filter(device => {
      const tenantName = device.tenant || device.businessName || 'General';
      const matchesTenant = selectedTenant === 'TODOS' || tenantName === selectedTenant;
      const matchesSearch = device.deviceId?.toLowerCase().includes(searchQuery.toLowerCase()) ||
                            device.location?.toLowerCase().includes(searchQuery.toLowerCase());
      return matchesTenant && matchesSearch;
    });
  }, [devices, selectedTenant, searchQuery]);

  // Enviar comando remoto
  const sendCommand = async (deviceId, command, payload = {}) => {
    setBusyByDevice(curr => ({ ...curr, [deviceId]: true }));
    try {
      const res = await fetch('/api/v1/command', {
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

      {/* Grid de Dispositivos */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {filteredDevices.map(device => {
          const tenantName = device.tenant || device.businessName || 'General';
          const isBusy = busyByDevice[device.deviceId];

          return (
            <div key={device.deviceId || device._id} className="bg-white border rounded-xl shadow-sm p-5 flex flex-col justify-between">
              <div>
                <div className="flex justify-between items-start mb-3">
                  <div>
                    <span className="text-xs font-bold px-2 py-1 rounded bg-indigo-50 text-indigo-700">
                      🏢 {tenantName}
                    </span>
                    <h3 className="text-md font-bold text-gray-800 mt-2 font-mono">{device.deviceId}</h3>
                  </div>
                  <span className="text-xs px-2 py-1 bg-gray-100 text-gray-600 rounded">
                    v{device.appVersion || '1.0.0'}
                  </span>
                </div>

                {/* Ubicación y Estado de Hardware */}
                <div className="space-y-1.5 text-xs text-gray-600 mb-4 bg-gray-50 p-3 rounded-lg border">
                  <p>📍 <strong>Ubicación:</strong> {device.location || 'No registrada'}</p>
                  <p>🔋 <strong>Batería:</strong> {device.batteryLevel ?? 'N/A'}% | 📶 <strong>Red:</strong> {device.wifiSignal || 'Wi-Fi'}</p>
                  <p>📦 <strong>Almacenamiento Libre:</strong> {device.storageFree ? `${device.storageFree} MB` : 'N/A'}</p>
                </div>
              </div>

              {/* Controles Remotos por Tableta */}
              <div className="border-t pt-3 flex flex-col gap-2">
                <div className="grid grid-cols-2 gap-2">
                  <button 
                    disabled={isBusy}
                    onClick={() => sendCommand(device.deviceId, 'RELOAD')}
                    className="bg-amber-500 hover:bg-amber-600 text-white text-xs py-1.5 px-3 rounded font-medium transition"
                  >
                    Recargar
                  </button>
                  <button 
                    disabled={isBusy}
                    onClick={() => sendCommand(device.deviceId, 'CLEAR_CACHE')}
                    className="bg-slate-700 hover:bg-slate-800 text-white text-xs py-1.5 px-3 rounded font-medium transition"
                  >
                    Limpiar Caché
                  </button>
                </div>
              </div>
            </div>
          );
        })}
      </div>

      {filteredDevices.length === 0 && (
        <div className="text-center py-16 text-gray-400 bg-white rounded-xl border mt-4">
          No hay tabletas registradas o que coincidan con el filtro seleccionado.
        </div>
      )}
    </div>
  );
}
