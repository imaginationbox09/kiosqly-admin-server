# Guía de Refactorización: Vista Agrupada por Negocio

## ✅ Cambios Realizados

### 1. **Modelo Backend (Device.js)**
Se agregaron nuevos campos al schema para soportar agrupación por negocio:

```javascript
// Campos de negocio/tenant
businessId: { type: String, default: null },
businessName: { type: String, default: null },
tenant: { type: String, default: null },

// Campos de ubicación y hardware
location: { type: String, default: null },
batteryLevel: { type: Number, default: null },
wifiSignal: { type: String, default: 'N/A' },
wifiSsid: { type: String, default: null },
ramFreeMb: { type: Number, default: null },
ramTotalMb: { type: Number, default: null },
storageFreeMb: { type: Number, default: null },
storageTotalMb: { type: Number, default: null },
brightness: { type: Number, default: null },
volume: { type: Number, default: null },
gps: { type: String, default: null },
ipAddress: { type: String, default: null },
ip: { type: String, default: null }
```

### 2. **Componente Frontend (KiosksAdmin.jsx)**
Se refactorizó completamente la vista para:

#### **a) Agrupación por Negocio**
- Nuevo estado: `expandedBusinesses` para controlar acordeones
- Nueva función `useMemo`: `groupedByBusiness` que agrupa dispositivos
- Función `filteredGroupedDevices` que mantiene la agrupación al filtrar
- Función `countOnlineByBusiness` que cuenta dispositivos conectados por negocio

#### **b) Interfaz Visual**
- **Acordeones por Negocio**: Cada negocio tiene su propia sección expandible
- **Indicadores**: Muestra cuántos dispositivos están en línea vs total por negocio
- **Icono Dinámico**: 🏢 para negocios normales, 📭 para "Sin Asignar"
- **Estado Visual**: Dispositivos online con fondo verde, offline con opacidad reducida
- **Expandible por Defecto**: Todos los acordeones abiertos al inicio

#### **c) Funcionabilidad Preservada**
- ✅ Todos los comandos remotos funcionan igual
- ✅ Búsqueda y filtros funcionan en cada grupo
- ✅ Actualización automática cada 10 segundos
- ✅ Notificaciones Toast para acciones

---

## 📊 Estructura de Datos Esperada

El backend debe enviar dispositivos con la siguiente estructura:

```json
[
  {
    "deviceId": "TB305XU-001",
    "alias": "Caja Principal",
    "name": "Quiosco TB305XU",
    "businessName": "Negocio A",
    "businessId": "biz_001",
    "tenant": "Negocio A",
    "status": "ONLINE",
    "location": "Local Centro",
    "localIp": "192.168.1.100",
    "batteryLevel": 85,
    "wifiSignal": "Excelente",
    "wifiSsid": "WiFi-Negocio-A",
    "ramFreeMb": 1024,
    "ramTotalMb": 2048,
    "storageFreeMb": 512,
    "storageTotalMb": 1024,
    "brightness": 100,
    "volume": 80,
    "gps": "40.4168°N, 3.7038°W",
    "appVersion": "2.5.1",
    "lastPing": "2026-09-09T10:30:00Z"
  },
  {
    "deviceId": "TB305FU-002",
    "alias": "Entrada",
    "businessName": "Negocio B",
    "status": "ONLINE",
    "location": "Entrada Principal",
    "localIp": "192.168.1.101",
    "appVersion": "2.5.0",
    "lastPing": "2026-09-09T10:29:55Z"
  },
  {
    "deviceId": "TB305XU-003",
    "alias": "Sin Asignar",
    "businessName": null,
    "tenant": null,
    "status": "OFFLINE",
    "location": "Almacén",
    "localIp": "192.168.1.102",
    "appVersion": "2.4.9",
    "lastPing": "2026-09-09T08:00:00Z"
  }
]
```

---

## 🔧 Cómo Actualizar tu Backend

### Opción 1: Flask/Python (admin_server.py)

```python
from datetime import datetime

# En tu endpoint GET /api/v1/kiosks
@app.route('/api/v1/kiosks', methods=['GET'])
def get_kiosks():
    devices = Device.find()  # De tu base de datos
    
    result = []
    for device in devices:
        result.append({
            'deviceId': device['deviceId'],
            'alias': device.get('alias'),
            'name': device.get('name'),
            'businessName': device.get('businessName', None),
            'businessId': device.get('businessId', None),
            'tenant': device.get('tenant', None),
            'status': device.get('status', 'OFFLINE'),
            'location': device.get('location', None),
            'localIp': device.get('localIp'),
            'batteryLevel': device.get('batteryLevel'),
            'wifiSignal': device.get('wifiSignal', 'N/A'),
            'wifiSsid': device.get('wifiSsid'),
            'ramFreeMb': device.get('ramFreeMb'),
            'ramTotalMb': device.get('ramTotalMb'),
            'storageFreeMb': device.get('storageFreeMb'),
            'storageTotalMb': device.get('storageTotalMb'),
            'brightness': device.get('brightness'),
            'volume': device.get('volume'),
            'gps': device.get('gps'),
            'appVersion': device.get('appVersion', '1.0.0'),
            'lastPing': device.get('lastPing', datetime.now()).isoformat()
        })
    
    return jsonify(result)
```

### Opción 2: Node.js/Express (kioskRoutes.js)

```javascript
router.get('/', async (req, res) => {
    try {
        const devices = await Device.find().sort({ lastPing: -1 });
        
        const response = devices.map(device => ({
            deviceId: device.deviceId,
            alias: device.alias,
            name: device.name,
            businessName: device.businessName,
            businessId: device.businessId,
            tenant: device.tenant,
            status: device.status,
            location: device.location,
            localIp: device.localIp,
            batteryLevel: device.batteryLevel,
            wifiSignal: device.wifiSignal,
            wifiSsid: device.wifiSsid,
            ramFreeMb: device.ramFreeMb,
            ramTotalMb: device.ramTotalMb,
            storageFreeMb: device.storageFreeMb,
            storageTotalMb: device.storageTotalMb,
            brightness: device.brightness,
            volume: device.volume,
            gps: device.gps,
            appVersion: device.appVersion || '1.0.0',
            lastPing: device.lastPing
        }));
        
        res.status(200).json({ success: true, data: response });
    } catch (error) {
        res.status(500).json({ success: false, error: error.message });
    }
});
```

---

## 🎯 Características Principales

### 1. **Agrupación Automática**
- Los dispositivos se agrupan automáticamente por `tenant` → `businessName` → `"Sin Asignar"`
- Orden: Se mantiene orden alfabético de negocios, con "Sin Asignar" al final

### 2. **Contadores por Negocio**
- Cada encabezado muestra: `X en línea de Y dispositivos`
- Se actualiza automáticamente cada 10 segundos
- Usa el campo `status === 'ONLINE'` para contar

### 3. **Filtrado Inteligente**
- El filtro de negocio ("TODOS", "Negocio A", etc.) ahora muestra solo ese negocio
- La búsqueda funciona dentro de cada grupo
- Si no hay resultados en un grupo, ese grupo no se muestra

### 4. **Indicadores Visuales**
```
🟢 En Línea   → Dispositivo conectado (fondo verde suave)
🔴 Desconectado → Dispositivo offline (opacidad reducida)

🏢 Negocio A  → Negocio normal
📭 Sin Asignar → Dispositivos sin asignar
```

### 5. **Acordeones Expandibles**
- Click en el encabezado para contraer/expandir
- Flecha (▼) rota cuando está contraído
- Todos expandidos por defecto

---

## 🚀 Cómo Probar

### Test 1: Verificar Agrupación
1. Abre la consola del navegador (F12)
2. Verifica que en Network > Fetch/XHR → `/api/v1/kiosks` devuelva dispositivos con `businessName`
3. Los dispositivos deben aparecer en sus grupos correspondientes

### Test 2: Verificar Contadores
1. Marca algunos dispositivos con `status: "OFFLINE"` en tu base de datos
2. Recarga la página
3. Verifica que el contador muestre correctamente (ej: "2 en línea de 5 dispositivos")

### Test 3: Verificar Filtros
1. Selecciona un negocio del dropdown
2. Solo deben aparecer dispositivos de ese negocio
3. Busca por ID o ubicación - debe filtrar dentro del grupo

### Test 4: Verificar Comandos
1. Haz click en "Recargar" o "Bloquear"
2. Debe enviar el comando correctamente
3. Toast debe aparecer con confirmación

---

## 🔄 Migrando Datos Existentes

Si ya tienes dispositivos en la base de datos sin los campos nuevos, puedes migrar así:

### Python/Flask
```python
# Script de migración
def migrate_devices():
    devices = db.devices.find()
    for device in devices:
        db.devices.update_one(
            {'_id': device['_id']},
            {'$set': {
                'businessName': None,
                'businessId': None,
                'tenant': None,
                'location': None,
                'batteryLevel': None,
                'wifiSignal': 'N/A',
                'wifiSsid': None,
                'ramFreeMb': None,
                'ramTotalMb': None,
                'storageFreeMb': None,
                'storageTotalMb': None,
                'brightness': None,
                'volume': None,
                'gps': None,
                'ipAddress': None,
                'ip': None
            }}
        )
```

### Node.js/Mongoose
```javascript
async function migrateDevices() {
    const schema = {
        businessName: null,
        businessId: null,
        tenant: null,
        location: null,
        batteryLevel: null,
        wifiSignal: 'N/A',
        wifiSsid: null,
        ramFreeMb: null,
        ramTotalMb: null,
        storageFreeMb: null,
        storageTotalMb: null,
        brightness: null,
        volume: null,
        gps: null,
        ipAddress: null,
        ip: null
    };
    
    await Device.updateMany({}, { $set: schema });
}
```

---

## 📱 Ejemplo de Respuesta Actualizada

Cuando tu dispositivo hace ping (`POST /api/v1/ping`), puede enviar:

```json
{
  "deviceId": "TB305XU-001",
  "localIp": "192.168.1.100",
  "appVersion": "2.5.1",
  "status": "ONLINE",
  "businessName": "Negocio A",
  "location": "Local Centro",
  "batteryLevel": 85,
  "wifiSignal": "Excelente",
  "wifiSsid": "WiFi-Negocio-A",
  "ramFreeMb": 1024,
  "ramTotalMb": 2048,
  "storageFreeMb": 512,
  "storageTotalMb": 1024,
  "brightness": 100,
  "volume": 80,
  "gps": "40.4168°N, 3.7038°W"
}
```

El backend actualizará estos campos automáticamente.

---

## ⚙️ Variables Importantes en React

```javascript
// Estado global
expandedBusinesses[businessName]  // Boolean: si está expandido

// Datos calculados
groupedByBusiness                 // Objeto con grupos por negocio
filteredGroupedDevices           // Grupos filtrados por búsqueda y tenant
countOnlineByBusiness            // Contador de dispositivos online por negocio
```

---

## 🐛 Solución de Problemas

### Problema: Los dispositivos no se agrupan
**Solución**: Verifica que tu backend esté enviando `businessName` o `tenant` en la respuesta.

### Problema: El contador muestra 0 online
**Solución**: Asegúrate que los dispositivos tengan `status: 'ONLINE'` (mayúsculas).

### Problema: Los acordeones no funcionan
**Solución**: Verifica que `expandedBusinesses` esté siendo actualizado correctamente en el onClick.

### Problema: La búsqueda no funciona
**Solución**: La búsqueda es case-insensitive pero busca en `deviceId`, `alias`, `name` y `location`. Verifica que estos campos tengan valores.

---

## 📝 Notas Finales

✅ **Funcionalidad Preservada**:
- Todos los comandos remotos funcionan igual
- Actualización automática cada 10 segundos
- Notificaciones Toast
- Búsqueda y filtros

✅ **Nuevas Características**:
- Agrupación visual por negocio
- Contadores de dispositivos online
- Acordeones expandibles
- Indicadores de estado visual

✅ **Escalabilidad**:
- Soporta cualquier número de negocios
- El filtrado es eficiente con `useMemo`
- No afecta el rendimiento

¡La refactorización está completa y lista para usar!
