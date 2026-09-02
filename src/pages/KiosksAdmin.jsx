import React, { useState, useEffect } from 'react';

const KiosksAdmin = () => {
    const [devices, setDevices] = useState([]);
    const [loading, setLoading] = useState(true);

    // Obtener la lista de tabletas desde el backend en Render
    const fetchDevices = async () => {
        try {
            const res = await fetch('https://kiosqly-admin-server.onrender.com/api/v1/kiosks');
            const data = await res.json();
            if (data.success) {
                setDevices(data.data);
            }
        } catch (error) {
            console.error('Error al cargar dispositivos:', error);
        } finally {
            setLoading(false);
        }
    };

    // Enviar comandos remotos (RELOAD, CLEAR_CACHE, etc.)
    const sendCommand = async (deviceId, command) => {
        try {
            const res = await fetch(`https://kiosqly-admin-server.onrender.com/api/v1/kiosks/${deviceId}/command`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ command })
            });
            const data = await res.json();
            if (data.success) {
                alert(`Comando ${command} enviado con éxito`);
            }
        } catch (error) {
            alert('Error al enviar el comando');
        }
    };

    useEffect(() => {
        fetchDevices();
        const interval = setInterval(fetchDevices, 10000); // Refrescar estado cada 10 seg
        return () => clearInterval(interval);
    }, []);

    // Agrupar tabletas por restaurante
    const groupedDevices = devices.reduce((acc, device) => {
        const rest = device.restaurantId || 'Sin Asignar';
        if (!acc[rest]) acc[rest] = [];
        acc[rest].push(device);
        return acc;
    }, {});

    if (loading) return <div style={{ padding: '20px' }}>Cargando quioscos...</div>;

    return (
        <div style={{ padding: '24px', fontFamily: 'sans-serif' }}>
            <h1 style={{ fontSize: '24px', fontWeight: 'bold', marginBottom: '20px' }}>
                Soporte y Control Remoto de Tabletas
            </h1>

            {Object.keys(groupedDevices).length === 0 ? (
                <p>No hay tabletas registradas aún.</p>
            ) : (
                Object.entries(groupedDevices).map(([restaurant, kioskList]) => (
                    <div key={restaurant} style={{ marginBottom: '32px', background: '#f8fafc', padding: '16px', borderRadius: '12px' }}>
                        <h2 style={{ fontSize: '18px', fontWeight: '600', marginBottom: '12px', color: '#334155' }}>
                            Restaurante: {restaurant}
                        </h2>
                        
                        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))', gap: '16px' }}>
                            {kioskList.map((kiosk) => {
                                // Determinar si está ONLINE (ping hace menos de 60 segundos)
                                const isOnline = (new Date() - new Date(kiosk.lastPing)) < 60000;

                                return (
                                    <div key={kiosk.deviceId} style={{ background: '#ffffff', border: '1px solid #e2e8f0', borderRadius: '8px', padding: '16px', boxShadow: '0 1px 3px rgba(0,0,0,0.1)' }}>
                                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
                                            <strong style={{ fontSize: '16px' }}>{kiosk.name}</strong>
                                            <span style={{
                                                fontSize: '12px',
                                                padding: '4px 8px',
                                                borderRadius: '12px',
                                                fontWeight: 'bold',
                                                backgroundColor: isOnline ? '#dcfce7' : '#fee2e2',
                                                color: isOnline ? '#166534' : '#991b1b'
                                            }}>
                                                {isOnline ? 'ONLINE' : 'OFFLINE'}
                                            </span>
                                        </div>

                                        <div style={{ fontSize: '13px', color: '#64748b', marginBottom: '16px', lineHeight: '1.5' }}>
                                            <div><strong>IP Local:</strong> {kiosk.localIp}</div>
                                            <div><strong>IP Pública:</strong> {kiosk.publicIp || 'N/A'}</div>
                                            <div><strong>ID:</strong> {kiosk.deviceId}</div>
                                            <div><strong>Versión:</strong> {kiosk.appVersion || '1.0.0'}</div>
                                        </div>

                                        <div style={{ display: 'flex', gap: '8px' }}>
                                            <button 
                                                onClick={() => sendCommand(kiosk.deviceId, 'RELOAD')}
                                                style={{ flex: 1, padding: '8px', background: '#eff6ff', color: '#1d4ed8', border: '1px solid #bfdbfe', borderRadius: '6px', cursor: 'pointer', fontWeight: '500' }}>
                                                🔄 Recargar
                                            </button>
                                            <button 
                                                onClick={() => sendCommand(kiosk.deviceId, 'CLEAR_CACHE')}
                                                style={{ flex: 1, padding: '8px', background: '#fffbeb', color: '#b45309', border: '1px solid #fde68a', borderRadius: '6px', cursor: 'pointer', fontWeight: '500' }}>
                                                🧹 Limpiar
                                            </button>
                                        </div>
                                    </div>
                                );
                            })}
                        </div>
                    </div>
                ))
            )}
        </div>
    );
};

export default KiosksAdmin;
