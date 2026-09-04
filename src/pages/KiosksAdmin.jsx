import React, { useEffect, useMemo, useState } from 'react';

const API_URL = 'https://kiosqly-admin-server-global.vercel.app';
const PAGE_SIZE = 12;
const ui = {
    page: { minHeight: '100vh', padding: '28px', background: '#eef2f6', color: '#132238', fontFamily: 'Inter, ui-sans-serif, system-ui, sans-serif' },
    shell: { maxWidth: '1480px', margin: '0 auto' },
    panel: { background: '#fff', border: '1px solid #dce4ee', borderRadius: '14px', boxShadow: '0 8px 24px rgba(32, 53, 82, .06)' },
    muted: { color: '#6c7b90' },
    button: { border: 0, borderRadius: '8px', minHeight: '36px', padding: '0 12px', cursor: 'pointer', fontWeight: 700, fontSize: '12px' },
};
const commands = { RELOAD: 'Reiniciar app', SYNC_DATA: 'Sincronizar', MAINTENANCE_MESSAGE: 'Aviso operador', KIOSK_LOCK: 'Bloquear kiosco', KIOSK_UNLOCK: 'Desbloquear kiosco' };
const valueOf = (device, camel, snake, fallback = '') => device[camel] ?? device[snake] ?? fallback;
const normalize = (device) => ({ ...device, id: valueOf(device, 'deviceId', 'device_id', 'sin-id'), tenant: valueOf(device, 'restaurantId', 'restaurant_id', 'Sin asignar'), name: valueOf(device, 'name', 'device_name', 'Tableta sin nombre'), location: valueOf(device, 'location', 'site_address', 'Ubicacion no registrada'), lastPing: valueOf(device, 'lastPing', 'last_seen', null), battery: Number(valueOf(device, 'battery', 'battery_percent', 0)), signal: Number(valueOf(device, 'wifiSignalStrength', 'wifi_signal_strength', 0)), version: valueOf(device, 'appVersion', 'app_version', 'N/D') });
const connectionOf = (device) => {
    const lastPing = device.lastPing ? new Date(device.lastPing).getTime() : 0;
    const online = device.status === 'ONLINE' && lastPing > 0 && Date.now() - lastPing < 90000;
    if (!online) return { label: 'Offline', color: '#d64545', background: '#fff0f0' };
    if (device.battery <= 20 || (device.signal > 0 && device.signal <= 30)) return { label: 'Advertencia', color: '#b7791f', background: '#fff9e8' };
    return { label: 'Online', color: '#21865b', background: '#eaf8f1' };
};
const formatTime = (date) => date ? new Date(date).toLocaleString('es-ES', { dateStyle: 'short', timeStyle: 'short' }) : 'Sin reporte';

const Metric = ({ label, value, color }) => <div style={{ padding: '18px 20px', borderRight: '1px solid #e4eaf1', minWidth: '150px', flex: 1 }}><div style={{ ...ui.muted, fontSize: '12px', fontWeight: 700 }}>{label}</div><strong style={{ display: 'block', marginTop: '7px', fontSize: '25px', color: color || '#132238' }}>{value}</strong></div>;

const DeviceCard = ({ device, onCommand, busy }) => {
    const connection = connectionOf(device);
    const runCommand = (command) => {
        const message = command === 'MAINTENANCE_MESSAGE' ? window.prompt('Mensaje para el operador:') : null;
        if (command !== 'MAINTENANCE_MESSAGE' || message) onCommand(device.id, command, message ? { message } : {});
    };
    return <article style={{ ...ui.panel, padding: '18px', display: 'flex', flexDirection: 'column', gap: '16px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', gap: '12px' }}><div style={{ minWidth: 0 }}><div style={{ fontSize: '11px', color: '#718096', fontWeight: 800, letterSpacing: '.08em' }}>{device.id}</div><h3 style={{ margin: '5px 0 0', fontSize: '18px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{device.name}</h3></div><span style={{ alignSelf: 'flex-start', borderRadius: '999px', padding: '6px 9px', color: connection.color, background: connection.background, fontSize: '11px', fontWeight: 800 }}>{connection.label}</span></div>
        <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}><span style={{ color: '#40516b', background: '#f1f5f9', borderRadius: '6px', padding: '5px 8px', fontSize: '12px' }}>Sede: {device.location}</span><span style={{ color: '#40516b', background: '#f1f5f9', borderRadius: '6px', padding: '5px 8px', fontSize: '12px' }}>v{device.version}</span></div>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px', padding: '12px', background: '#f7f9fc', borderRadius: '9px' }}><div><span style={ui.muted}>Bateria</span><strong style={{ display: 'block', color: device.battery <= 20 ? '#c05621' : '#26364d' }}>{device.battery}% {device.is_charging ? '⚡' : ''}</strong></div><div><span style={ui.muted}>Senal Wi-Fi</span><strong style={{ display: 'block', color: device.signal > 0 && device.signal <= 30 ? '#c05621' : '#26364d' }}>{device.signal || 'N/D'}%</strong></div><div><span style={ui.muted}>Ultimo heartbeat</span><strong style={{ display: 'block', color: '#26364d', fontSize: '12px' }}>{formatTime(device.lastPing)}</strong></div><div><span style={ui.muted}>IP local</span><strong style={{ display: 'block', color: '#26364d', fontSize: '12px' }}>{valueOf(device, 'localIp', 'local_ip', 'N/D')}</strong></div></div>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, minmax(0, 1fr))', gap: '7px', marginTop: 'auto' }}>{Object.entries(commands).map(([command, label]) => <button key={command} type="button" disabled={busy} onClick={() => runCommand(command)} style={{ ...ui.button, color: command.includes('LOCK') ? '#9b2c2c' : '#3154b7', background: command.includes('LOCK') ? '#fff1f1' : '#edf2ff', opacity: busy ? .55 : 1 }}>{busy ? 'Enviando...' : label}</button>)}</div>
    </article>;
};

const TenantSection = ({ tenant, devices, expanded, onToggle, onCommand, busyByDevice }) => {
    const online = devices.filter((device) => connectionOf(device).label !== 'Offline').length;
    const warnings = devices.filter((device) => connectionOf(device).label === 'Advertencia').length;
    return <section style={{ marginBottom: '22px' }}><button type="button" onClick={onToggle} style={{ ...ui.panel, width: '100%', padding: '16px 18px', display: 'flex', alignItems: 'center', gap: '16px', textAlign: 'left', cursor: 'pointer' }}><span style={{ fontSize: '20px', color: '#4c6fff' }}>{expanded ? '−' : '+'}</span><span style={{ flex: 1 }}><strong style={{ display: 'block', fontSize: '16px' }}>{tenant}</strong><span style={{ ...ui.muted, fontSize: '12px' }}>Vista operativa por negocio</span></span><span style={{ fontSize: '12px', color: '#52647c' }}>{devices.length} total</span><span style={{ fontSize: '12px', color: '#21865b' }}>{online} online</span><span style={{ fontSize: '12px', color: warnings ? '#b7791f' : '#8b99aa' }}>{warnings} alertas</span></button>{expanded && <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(290px, 1fr))', gap: '14px', marginTop: '12px' }}>{devices.map((device) => <DeviceCard key={device.id} device={device} onCommand={onCommand} busy={busyByDevice[device.id]} />)}</div>}</section>;
};

const KiosksAdmin = () => {
    const [devices, setDevices] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState('');
    const [query, setQuery] = useState('');
    const [tenant, setTenant] = useState('TODOS');
    const [view, setView] = useState('grouped');
    const [page, setPage] = useState(1);
    const [expanded, setExpanded] = useState({});
    const [busyByDevice, setBusyByDevice] = useState({});
    const [toast, setToast] = useState('');

    const fetchDevices = async () => {
        try {
            const response = await fetch(`${API_URL}/api/v1/kiosks`);
            if (!response.ok) throw new Error(`API ${response.status}`);
            const data = await response.json();
            if (!data.success) throw new Error('La API no pudo devolver dispositivos');
            setDevices(data.data.map(normalize));
            setError('');
        } catch (fetchError) { console.error('Error al cargar dispositivos:', fetchError); setError('No se pudo conectar con el centro de control. Reintentando...'); }
        finally { setLoading(false); }
    };
    const sendCommand = async (deviceId, command, payload) => {
        setBusyByDevice((current) => ({ ...current, [deviceId]: true }));
        try {
            const response = await fetch(`${API_URL}/api/v1/kiosks/${encodeURIComponent(deviceId)}/command`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ command, ...payload }) });
            if (!response.ok) throw new Error(`API ${response.status}`);
            setToast(`${commands[command] || command} encolado para ${deviceId}`);
        } catch (commandError) { console.error('Error al enviar comando:', commandError); setToast('No se pudo enviar la accion'); }
        finally { setBusyByDevice((current) => ({ ...current, [deviceId]: false })); window.setTimeout(() => setToast(''), 3500); }
    };
    useEffect(() => { fetchDevices(); const interval = window.setInterval(fetchDevices, 10000); return () => window.clearInterval(interval); }, []);
    useEffect(() => setPage(1), [query, tenant, view]);

    const tenants = useMemo(() => [...new Set(devices.map((device) => device.tenant))].sort(), [devices]);
    const filtered = useMemo(() => devices.filter((device) => (tenant === 'TODOS' || device.tenant === tenant) && `${device.id} ${device.name} ${device.tenant} ${device.location}`.toLowerCase().includes(query.toLowerCase())), [devices, query, tenant]);
    const totalPages = Math.max(1, Math.ceil(filtered.length / PAGE_SIZE));
    const pageDevices = filtered.slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE);
    const grouped = pageDevices.reduce((groups, device) => ({ ...groups, [device.tenant]: [...(groups[device.tenant] || []), device] }), {});
    const online = devices.filter((device) => connectionOf(device).label !== 'Offline').length;
    const warnings = devices.filter((device) => connectionOf(device).label === 'Advertencia').length;

    if (loading) return <div style={{ ...ui.page, display: 'grid', placeItems: 'center' }}>Cargando centro de control...</div>;
    return <main style={ui.page}><div style={ui.shell}>
        <header><div style={{ color: '#4c6fff', fontSize: '11px', fontWeight: 800, letterSpacing: '.12em', textTransform: 'uppercase' }}>Kiosqly / Operations center</div><h1 style={{ margin: '8px 0 0', fontSize: 'clamp(26px, 3vw, 42px)', letterSpacing: '-.03em' }}>Control de hardware distribuido</h1><p style={{ ...ui.muted, margin: '9px 0 0' }}>Supervisa la salud operativa y actua sobre cada terminal desde un solo lugar.</p></header>
        <div style={{ ...ui.panel, display: 'flex', flexWrap: 'wrap', marginTop: '26px' }}><Metric label="Terminales" value={devices.length} /><Metric label="Online" value={online} color="#21865b" /><Metric label="Offline" value={devices.length - online} color="#d64545" /><Metric label="Alertas" value={warnings} color="#b7791f" /></div>
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '10px', alignItems: 'center', margin: '26px 0 18px' }}><input aria-label="Buscar terminal" value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Buscar ID, negocio o sede..." style={{ flex: '1 1 260px', minHeight: '42px', border: '1px solid #d5deea', borderRadius: '9px', padding: '0 13px' }} /><select aria-label="Filtrar negocio" value={tenant} onChange={(event) => setTenant(event.target.value)} style={{ minWidth: '190px', minHeight: '42px', border: '1px solid #d5deea', borderRadius: '9px', padding: '0 13px' }}><option value="TODOS">Todos los negocios</option>{tenants.map((item) => <option key={item} value={item}>{item}</option>)}</select><div style={{ ...ui.panel, display: 'flex', padding: '3px' }}><button type="button" onClick={() => setView('grouped')} style={{ ...ui.button, background: view === 'grouped' ? '#132238' : '#fff', color: view === 'grouped' ? '#fff' : '#61728a' }}>Por negocio</button><button type="button" onClick={() => setView('list')} style={{ ...ui.button, background: view === 'list' ? '#132238' : '#fff', color: view === 'list' ? '#fff' : '#61728a' }}>Lista</button></div></div>
        {error && <div role="alert" style={{ ...ui.panel, padding: '12px 15px', borderColor: '#f0c4c4', color: '#a33a3a', marginBottom: '18px' }}>{error}</div>}{toast && <div role="status" style={{ position: 'fixed', right: '24px', bottom: '24px', zIndex: 2, background: '#132238', color: '#fff', borderRadius: '9px', padding: '13px 16px' }}>{toast}</div>}
        {filtered.length === 0 ? <div style={{ ...ui.panel, padding: '50px', textAlign: 'center', ...ui.muted }}>No hay terminales que coincidan con el filtro actual.</div> : view === 'grouped' ? Object.entries(grouped).map(([group, groupDevices]) => <TenantSection key={group} tenant={group} devices={groupDevices} expanded={expanded[group] !== false} onToggle={() => setExpanded((current) => ({ ...current, [group]: current[group] === false }))} onCommand={sendCommand} busyByDevice={busyByDevice} />) : <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(290px, 1fr))', gap: '14px' }}>{pageDevices.map((device) => <DeviceCard key={device.id} device={device} onCommand={sendCommand} busy={busyByDevice[device.id]} />)}</div>}
        <footer style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '22px 0', ...ui.muted, fontSize: '12px' }}><span>Mostrando {pageDevices.length} de {filtered.length} terminales</span><div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}><button type="button" disabled={page === 1} onClick={() => setPage((current) => current - 1)} style={{ ...ui.button, background: '#fff', color: '#3154b7', border: '1px solid #d5deea' }}>Anterior</button><span>Pagina {page} / {totalPages}</span><button type="button" disabled={page === totalPages} onClick={() => setPage((current) => current + 1)} style={{ ...ui.button, background: '#fff', color: '#3154b7', border: '1px solid #d5deea' }}>Siguiente</button></div></footer>
    </div></main>;
};

export default KiosksAdmin;
