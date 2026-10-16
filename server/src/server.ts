// server/src/server.ts
import http from 'http';
import { WebSocketServer } from 'ws';
import express from 'express';
import { WebSocketManager } from './websocket';
import { ApiServer } from './api';

const app = express();
const server = http.createServer(app);
const wss = new WebSocketServer({ server });

const webSocketManager = new WebSocketManager();
const apiServer = new ApiServer(webSocketManager);

app.use(express.json());

// Setup WebSocket connections
wss.on('connection', (ws, req) => {
  const url = new URL(req.url || '', `http://${req.headers.host}`);
  const role = url.searchParams.get('role') || 'viewer';
  const pairingCode = url.searchParams.get('pairingCode');

  ws.role = role;
  console.log(`Client connected as ${role}, pairingCode: ${pairingCode || 'N/A'}`);

  if (pairingCode) {
    if (role === 'pc') {
      webSocketManager.addPCSocket(pairingCode, ws);
    } else if (role === 'mobile') {
      webSocketManager.addMobileSocket(pairingCode, ws);
    }

    // Send connection confirmation
    ws.send(JSON.stringify({
      type: 'info',
      message: `Connected as ${role} to pair ${pairingCode || 'N/A'}`,
      status: webSocketManager.getRoomStatus(pairingCode)
    }));

    // Check if pair is complete
    const room = webSocketManager.getRoom(pairingCode);
    if (room && room.pcSocket && room.mobileSocket) {
      room.pcSocket.send(JSON.stringify({
        type: 'pair-complete',
        message: 'Pair established successfully',
        status: webSocketManager.getRoomStatus(pairingCode)
      }));
      room.mobileSocket.send(JSON.stringify({
        type: 'pair-complete',
        message: 'Pair established successfully',
        status: webSocketManager.getRoomStatus(pairingCode)
      }));
      console.log(`Pair ${pairingCode} established: both devices connected`);
    }
  }

  ws.on('message', (data) => {
    try {
      const messageData = JSON.parse(data.toString());
      const pairingCode = ws.pairingCode;
      const room = pairingCode ? webSocketManager.getRoom(pairingCode) : null;

      if (!room) return;

      // Route message based on type
      switch (messageData.type) {
        case 'key':
          if (ws.role === 'mobile' && room.keyboardEnabled) {
            const encrypted = room.encryption.encrypt(messageData);
            if (room.pcSocket?.readyState === WebSocket.OPEN) {
              room.pcSocket.send(encrypted);
            }
          }
          break;

        case 'clipboard-set':
          if (ws.role === 'pc') {
            webSocketManager.forwardClipboard(room, messageData.data);
          }
          break;

        case 'keyboard-toggle':
          if (ws.role === 'pc' && messageData.enabled !== undefined) {
            room.keyboardEnabled = messageData.enabled;
            webSocketManager.sendKeyboardToggle(room, 'mobile', messageData.enabled);
          }
          break;
      }
    } catch (error) {
      console.error('Message handling error:', error);
    }
  });

  ws.on('close', () => {
    webSocketManager.removeSocket(ws);
    console.log(`Client disconnected: role=${ws.role}, pairingCode=${ws.pairingCode || 'unknown'}`);
  });
});

const PORT = process.env.PORT || 3000;
server.listen(PORT, '0.0.0.0', () => {
  console.log(`Keyboard sync server running on http://0.0.0.0:${PORT}`);
  console.log('Mobile:  http://<host>:3000/?role=mobile');
  console.log('PC:      http://<host>:3000/?role=pc');
  console.log('Pairing: POST /api/pairing/generate');
});
