import express from 'express';
import Device from '../models/Device.js';

const router = express.Router();

// Ping desde tabletas
router.post('/ping', async (req, res) => {
    try {
        const { deviceId, localIp, appVersion, status } = req.body;
        const publicIp = req.headers['x-forwarded-for'] || req.socket.remoteAddress;

        let device = await Device.findOne({ deviceId });

        if (!device) {
            device = new Device({ deviceId, localIp, publicIp, appVersion, status });
        } else {
            device.localIp = localIp;
            device.publicIp = publicIp;
            device.appVersion = appVersion || device.appVersion;
            device.status = status || 'ONLINE';
            device.lastPing = new Date();
        }

        const commandToSend = device.pendingCommand;
        device.pendingCommand = null;

        await device.save();

        res.status(200).json({
            success: true,
            command: commandToSend
        });
    } catch (error) {
        res.status(500).json({ success: false, error: error.message });
    }
});

// Enviar comandos desde Admin Panel
router.post('/:deviceId/command', async (req, res) => {
    try {
        const { deviceId } = req.params;
        const { command } = req.body;

        const device = await Device.findOne({ deviceId });
        if (!device) {
            return res.status(404).json({ success: false, message: 'Dispositivo no encontrado' });
        }

        device.pendingCommand = command;
        await device.save();

        res.status(200).json({ success: true, message: `Comando ${command} encolado` });
    } catch (error) {
        res.status(500).json({ success: false, error: error.message });
    }
});

// Listar dispositivos
router.get('/', async (req, res) => {
    try {
        const devices = await Device.find().sort({ lastPing: -1 });
        res.status(200).json({ success: true, data: devices });
    } catch (error) {
        res.status(500).json({ success: false, error: error.message });
    }
});

export default router;
