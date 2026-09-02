import mongoose from 'mongoose';

const DeviceSchema = new mongoose.Schema({
    deviceId: { type: String, required: true, unique: true },
    restaurantId: { type: String, default: 'unassigned' },
    name: { type: String, default: 'Nuevo Quiosco' },
    localIp: { type: String, required: true },
    publicIp: { type: String },
    appVersion: { type: String },
    status: { type: String, enum: ['ONLINE', 'OFFLINE'], default: 'ONLINE' },
    pendingCommand: { type: String, default: null },
    lastPing: { type: Date, default: Date.now }
}, { timestamps: true });

export default mongoose.model('Device', DeviceSchema);
