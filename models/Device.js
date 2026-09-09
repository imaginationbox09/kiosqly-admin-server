import mongoose from 'mongoose';

const DeviceSchema = new mongoose.Schema({
    deviceId: { type: String, required: true, unique: true },
    restaurantId: { type: String, default: 'unassigned' },
    name: { type: String, default: 'Nuevo Quiosco' },
    alias: { type: String },
    localIp: { type: String, required: true },
    publicIp: { type: String },
    appVersion: { type: String },
    status: { type: String, enum: ['ONLINE', 'OFFLINE'], default: 'ONLINE' },
    pendingCommand: { type: String, default: null },
    lastPing: { type: Date, default: Date.now },
    
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
}, { timestamps: true });

export default mongoose.model('Device', DeviceSchema);
