# Ejemplos de Actualización de Datos

## 📋 Estructura Completa de un Dispositivo

```json
{
  "_id": "507f1f77bcf86cd799439011",
  "deviceId": "TB305XU-001",
  "alias": "Caja Principal",
  "name": "Quiosco TB305XU",
  "restaurantId": "rest_001",
  
  // DATOS DE NEGOCIO/TENANT
  "businessName": "Negocio A",
  "businessId": "biz_001", 
  "tenant": "Negocio A",
  
  // UBICACIÓN Y CONEXIÓN
  "location": "Local Centro",
  "localIp": "192.168.1.100",
  "publicIp": "203.0.113.45",
  
  // ESTADO DEL DISPOSITIVO
  "status": "ONLINE",
  "appVersion": "2.5.1",
  "lastPing": "2026-09-09T10:30:00Z",
  
  // HARDWARE Y CONECTIVIDAD
  "batteryLevel": 85,
  "wifiSignal": "Excelente",
  "wifiSsid": "WiFi-Negocio-A",
  "wifiPassword": "****", // No enviar al frontend
  
  // MEMORIA Y ALMACENAMIENTO
  "ramFreeMb": 1024,
  "ramTotalMb": 2048,
  "storageFreeMb": 512,
  "storageTotalMb": 1024,
  
  // CONFIGURACIÓN
  "brightness": 100,
  "volume": 80,
  "gps": "40.4168°N, 3.7038°W",
  
  // COMANDOS
  "pendingCommand": null,
  
  // METADATOS
  "createdAt": "2026-09-01T08:00:00Z",
  "updatedAt": "2026-09-09T10:30:00Z"
}
```

---

## 🔄 MongoDB - Queries de Actualización

### Asignar dispositivo a un negocio

```javascript
// Asignar TB305XU-001 a "Negocio A"
db.devices.updateOne(
  { deviceId: "TB305XU-001" },
  { $set: {
    businessName: "Negocio A",
    businessId: "biz_001",
    tenant: "Negocio A",
    location: "Local Centro"
  }}
)
```

### Reasignar varios dispositivos a un negocio

```javascript
// Asignar todos los dispositivos que empiezan con "TB305XU" a "Negocio B"
db.devices.updateMany(
  { deviceId: { $regex: "^TB305XU" } },
  { $set: {
    businessName: "Negocio B",
    businessId: "biz_002",
    tenant: "Negocio B"
  }}
)
```

### Actualizar información de hardware

```javascript
// Actualizar info de red y hardware para un dispositivo
db.devices.updateOne(
  { deviceId: "TB305XU-001" },
  { $set: {
    batteryLevel: 75,
    wifiSignal: "Buena",
    wifiSsid: "WiFi-Negocio-A",
    ramFreeMb: 1024,
    ramTotalMb: 2048,
    storageFreeMb: 512,
    storageTotalMb": 1024,
    brightness: 100,
    volume: 80,
    gps: "40.4168°N, 3.7038°W",
    lastPing: new Date()
  }}
)
```

### Desasignar dispositivo (moverlo a "Sin Asignar")

```javascript
db.devices.updateOne(
  { deviceId: "TB305XU-003" },
  { $set: {
    businessName: null,
    businessId: null,
    tenant: null
  }}
)
```

### Cambiar ubicación de dispositivo

```javascript
db.devices.updateOne(
  { deviceId: "TB305XU-001" },
  { $set: {
    location: "Nueva Ubicación"
  }}
)
```

### Listar dispositivos por negocio

```javascript
// Todos los dispositivos de "Negocio A"
db.devices.find({ 
  businessName: "Negocio A" 
}).pretty()

// Dispositivos sin asignar
db.devices.find({ 
  businessName: null 
}).pretty()

// Dispositivos online de un negocio
db.devices.find({
  businessName: "Negocio A",
  status: "ONLINE"
}).pretty()
```

### Contar dispositivos

```javascript
// Total de dispositivos
db.devices.countDocuments()

// Dispositivos por negocio
db.devices.aggregate([
  { $group: {
    _id: "$businessName",
    count: { $sum: 1 },
    online: { $sum: { $cond: [{ $eq: ["$status", "ONLINE"] }, 1, 0] } }
  }},
  { $sort: { count: -1 } }
])
```

### Crear índices para mejor rendimiento

```javascript
// Índice por businessName para búsquedas rápidas
db.devices.createIndex({ businessName: 1 })

// Índice por status para filtros
db.devices.createIndex({ status: 1 })

// Índice compuesto para búsquedas frecuentes
db.devices.createIndex({ businessName: 1, status: 1 })

// Índice por deviceId (ya debería existir como unique)
db.devices.createIndex({ deviceId: 1 }, { unique: true })
```

---

## 🐍 Python/PyMongo - Ejemplos de Actualización

### Instalación
```bash
pip install pymongo
```

### Script de actualización

```python
from pymongo import MongoClient
from datetime import datetime

# Conectar a MongoDB
client = MongoClient('mongodb://localhost:27017/')
db = client['kiosqly_admin']
devices = db.devices

# 1. Asignar dispositivo a negocio
def assign_device_to_business(device_id, business_name, business_id, location):
    devices.update_one(
        {'deviceId': device_id},
        {'$set': {
            'businessName': business_name,
            'businessId': business_id,
            'tenant': business_name,
            'location': location
        }}
    )
    print(f"Dispositivo {device_id} asignado a {business_name}")

# 2. Actualizar info de hardware
def update_device_hardware(device_id, battery, wifi_ssid, ram_free, ram_total):
    devices.update_one(
        {'deviceId': device_id},
        {'$set': {
            'batteryLevel': battery,
            'wifiSsid': wifi_ssid,
            'ramFreeMb': ram_free,
            'ramTotalMb': ram_total,
            'lastPing': datetime.now()
        }}
    )
    print(f"Hardware de {device_id} actualizado")

# 3. Listar dispositivos por negocio
def get_devices_by_business(business_name):
    devices_list = list(devices.find({'businessName': business_name}))
    return devices_list

# 4. Contar dispositivos online por negocio
def count_online_by_business():
    result = devices.aggregate([
        {'$group': {
            '_id': '$businessName',
            'total': {'$sum': 1},
            'online': {'$sum': {'$cond': [{'$eq': ['$status', 'ONLINE']}, 1, 0]}}
        }},
        {'$sort': {'total': -1}}
    ])
    return list(result)

# 5. Migración: inicializar nuevos campos
def migrate_all_devices():
    devices.update_many(
        {},
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
    print("Migración completada")

# Uso
if __name__ == "__main__":
    # Asignar dispositivos
    assign_device_to_business("TB305XU-001", "Negocio A", "biz_001", "Local Centro")
    assign_device_to_business("TB305XU-002", "Negocio A", "biz_001", "Local Secundario")
    assign_device_to_business("TB305FU-001", "Negocio B", "biz_002", "Entrada")
    
    # Actualizar hardware
    update_device_hardware("TB305XU-001", 85, "WiFi-Negocio-A", 1024, 2048)
    
    # Listar dispositivos
    print("\nDispositivos de Negocio A:")
    for dev in get_devices_by_business("Negocio A"):
        print(f"  - {dev['deviceId']}: {dev['alias']}")
    
    # Contar online
    print("\nEstadísticas por negocio:")
    for stat in count_online_by_business():
        print(f"  {stat['_id']}: {stat['online']}/{stat['total']} en línea")
```

---

## 🟢 Node.js/Mongoose - Ejemplos de Actualización

```javascript
const mongoose = require('mongoose');

// Conectar a MongoDB
await mongoose.connect('mongodb://localhost:27017/kiosqly_admin');

const Device = require('./models/Device');

// 1. Asignar dispositivo a negocio
async function assignDeviceToBusiness(deviceId, businessName, businessId, location) {
    await Device.updateOne(
        { deviceId },
        { $set: {
            businessName,
            businessId,
            tenant: businessName,
            location
        }}
    );
    console.log(`Dispositivo ${deviceId} asignado a ${businessName}`);
}

// 2. Actualizar hardware
async function updateDeviceHardware(deviceId, hardwareData) {
    await Device.updateOne(
        { deviceId },
        { $set: {
            ...hardwareData,
            lastPing: new Date()
        }}
    );
    console.log(`Hardware de ${deviceId} actualizado`);
}

// 3. Listar dispositivos por negocio
async function getDevicesByBusiness(businessName) {
    return await Device.find({ businessName }).sort({ lastPing: -1 });
}

// 4. Contar online por negocio
async function countOnlineByBusiness() {
    return await Device.aggregate([
        { $group: {
            _id: '$businessName',
            total: { $sum: 1 },
            online: { $sum: { $cond: [{ $eq: ['$status', 'ONLINE'] }, 1, 0] } }
        }},
        { $sort: { total: -1 } }
    ]);
}

// 5. Migración
async function migrateDevices() {
    const updateObject = {
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
    
    await Device.updateMany({}, { $set: updateObject });
    console.log('Migración completada');
}

// Uso
(async () => {
    await assignDeviceToBusiness('TB305XU-001', 'Negocio A', 'biz_001', 'Local Centro');
    await assignDeviceToBusiness('TB305XU-002', 'Negocio A', 'biz_001', 'Local Secundario');
    
    await updateDeviceHardware('TB305XU-001', {
        batteryLevel: 85,
        wifiSignal: 'Excelente',
        wifiSsid: 'WiFi-Negocio-A',
        ramFreeMb: 1024,
        ramTotalMb: 2048
    });
    
    const devicesA = await getDevicesByBusiness('Negocio A');
    console.log('Dispositivos de Negocio A:', devicesA);
    
    const stats = await countOnlineByBusiness();
    console.log('Estadísticas:', stats);
    
    await mongoose.connection.close();
})();
```

---

## 🚀 Script SQL si usas PostgreSQL

```sql
-- Agregar columnas si no existen
ALTER TABLE devices ADD COLUMN IF NOT EXISTS business_name VARCHAR(255);
ALTER TABLE devices ADD COLUMN IF NOT EXISTS business_id VARCHAR(255);
ALTER TABLE devices ADD COLUMN IF NOT EXISTS tenant VARCHAR(255);
ALTER TABLE devices ADD COLUMN IF NOT EXISTS location VARCHAR(255);
ALTER TABLE devices ADD COLUMN IF NOT EXISTS battery_level INT;
ALTER TABLE devices ADD COLUMN IF NOT EXISTS wifi_signal VARCHAR(50);
ALTER TABLE devices ADD COLUMN IF NOT EXISTS wifi_ssid VARCHAR(255);
ALTER TABLE devices ADD COLUMN IF NOT EXISTS ram_free_mb INT;
ALTER TABLE devices ADD COLUMN IF NOT EXISTS ram_total_mb INT;
ALTER TABLE devices ADD COLUMN IF NOT EXISTS storage_free_mb INT;
ALTER TABLE devices ADD COLUMN IF NOT EXISTS storage_total_mb INT;
ALTER TABLE devices ADD COLUMN IF NOT EXISTS brightness INT;
ALTER TABLE devices ADD COLUMN IF NOT EXISTS volume INT;
ALTER TABLE devices ADD COLUMN IF NOT EXISTS gps VARCHAR(50);

-- Crear índices
CREATE INDEX idx_devices_business_name ON devices(business_name);
CREATE INDEX idx_devices_status ON devices(status);
CREATE INDEX idx_devices_business_status ON devices(business_name, status);

-- Actualizar dispositivo
UPDATE devices 
SET business_name = 'Negocio A',
    business_id = 'biz_001',
    tenant = 'Negocio A',
    location = 'Local Centro',
    battery_level = 85
WHERE device_id = 'TB305XU-001';

-- Listar por negocio
SELECT * FROM devices 
WHERE business_name = 'Negocio A' 
ORDER BY last_ping DESC;

-- Contar online por negocio
SELECT 
  business_name,
  COUNT(*) as total,
  SUM(CASE WHEN status = 'ONLINE' THEN 1 ELSE 0 END) as online
FROM devices
GROUP BY business_name
ORDER BY total DESC;
```

---

## 📊 Datos de Prueba

Puedes usar este script para poblar datos de prueba:

### MongoDB

```javascript
db.devices.insertMany([
  {
    deviceId: "TB305XU-001",
    alias: "Caja Principal",
    name: "Quiosco TB305XU",
    businessName: "Negocio A",
    businessId: "biz_001",
    status: "ONLINE",
    location: "Local Centro",
    localIp: "192.168.1.100",
    appVersion: "2.5.1",
    batteryLevel: 85,
    wifiSignal: "Excelente",
    wifiSsid: "WiFi-Negocio-A",
    ramFreeMb: 1024,
    ramTotalMb: 2048,
    storageFreeMb: 512,
    storageTotalMb: 1024,
    brightness: 100,
    volume: 80,
    lastPing: new Date()
  },
  {
    deviceId: "TB305XU-002",
    alias: "Entrada",
    name: "Quiosco Entrada",
    businessName: "Negocio A",
    businessId: "biz_001",
    status: "ONLINE",
    location: "Local Secundario",
    localIp: "192.168.1.101",
    appVersion: "2.5.0",
    batteryLevel: 70,
    wifiSignal: "Buena",
    lastPing: new Date()
  },
  {
    deviceId: "TB305FU-001",
    alias: "Pantalla 1",
    businessName: "Negocio B",
    businessId: "biz_002",
    status: "ONLINE",
    location: "Entrada Principal",
    localIp: "192.168.1.102",
    appVersion: "2.5.1",
    batteryLevel: 90,
    lastPing: new Date()
  },
  {
    deviceId: "TB305FU-002",
    alias: "Sin Asignar",
    businessName: null,
    status: "OFFLINE",
    location: "Almacén",
    localIp: "192.168.1.103",
    appVersion: "2.4.9",
    lastPing: new Date(Date.now() - 3600000)
  }
])
```

---

## ✅ Checklist de Implementación

- [ ] Actualizar modelo Device.js con nuevos campos
- [ ] Actualizar endpoint GET `/api/v1/kiosks` para devolver nuevos campos
- [ ] Actualizar endpoint POST `/api/v1/kiosks/{id}/command` para recibir datos de hardware
- [ ] Ejecutar migración en base de datos existente
- [ ] Asignar dispositivos existentes a negocios
- [ ] Probar vista agrupada en navegador
- [ ] Verificar contadores de dispositivos
- [ ] Probar filtros por negocio
- [ ] Probar búsqueda dentro de grupos
- [ ] Verificar que comandos sigan funcionando
- [ ] Verificar actualización automática cada 10 segundos

¡Listo para implementar!
