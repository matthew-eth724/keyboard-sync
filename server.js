
const express = require('express');
const http = require('http');
const WebSocket = require('ws');
const crypto = require('crypto');
const { exec } = require('child_process');
const path = require('path');
const CryptoJS = require('crypto-js');

const app = express();
const server = http.createServer(app);
const wss = new WebSocket.Server({ server });

app.use(express.static(path.join(__dirname, 'public')));

app.get('/', (req, res) => {
  res.sendFile(path.join(__dirname, 'public', 'index.html'));
});

// Pairing code storage
const pairingCodes = new Map();
const connections = new Map();
const ENCRYPTION_KEY = crypto.randomBytes(32); // In production, use environment variable

// Generate random 6-digit pairing code
generatePairingCode = () => Math.floor(100000 + Math.random() * 900000).toString();

// Create WebSocket rooms for paired devices
class PairRoom {
  constructor(pairingCode) {
    this.pairingCode = pairingCode;
    this.pcSocket = null;
    this.mobileSocket = null;
    this.encrypted = false;
    this.keyboardEnabled = true;
    this.sharedKey = null;
    this.initEncryption();
  }

  initEncryption() {
    this.sharedKey = crypto.randomBytes(32);
  }

  encrypt(message) {
    const iv = crypto.randomBytes(16);
    const cipher = crypto.createCipheriv('aes-256-gcm', this.sharedKey, iv);
    let encrypted = cipher.update(JSON.stringify(message));
    encrypted = Buffer.concat([encrypted, cipher.final()]);
    const tag = cipher.getAuthTag();
    return Buffer.concat([iv, tag, encrypted]).toString('base64');
  }

  decrypt(encryptedData) {
    try {
      const buffer = Buffer.from(encryptedData, 'base64');
      const iv = buffer.slice(0, 16);
      const tag = buffer.slice(16, 32);
      const encrypted = buffer.slice(32);
      const decipher = crypto.createDecipheriv('aes-256-gcm', this.sharedKey, iv);
      decipher.setAuthTag(tag);
      let decrypted = decipher.update(encrypted);
      decrypted = Buffer.concat([decrypted, decipher.final()]);
      return JSON.parse(decrypted.toString());
    } catch (e) {
      console.log('Decryption error:', e.message);
      return null;
    }
  }

  addPCSocket(ws) {
    this.pcSocket = ws;
    this.pcSocket.pairingCode = this.pairingCode;
  }

  addMobileSocket(ws) {
    this.mobileSocket = ws;
    this.mobileSocket.pairingCode = this.pairingCode;
  }

  forwardKeyboardFromMobile(data) {
    if (!this.keyboardEnabled) return;
    
    const decrypted = this.decrypt(data);
    if (decrypted && decrypted.type === 'key' && this.pcSocket?.readyState === WebSocket.OPEN) {
      this.pcSocket.send(this.encrypt(decrypted));
    }
  }

  forwardClipboard(data) {
    if (this.mobileSocket?.readyState === WebSocket.OPEN) {
      this.mobileSocket.send(this.encrypt({ type: 'clipboard', data: data }));
    }
  }

  sendKeyboardToggle(to, enabled) {
    if (this.mobileSocket?.readyState === WebSocket.OPEN && to === 'mobile') {
      this.mobileSocket.send(this.encrypt({ type: 'keyboard-toggle', enabled: enabled }));
    }
    if (this.pcSocket?.readyState === WebSocket.OPEN && to === 'pc') {
      this.pcSocket.send(this.encrypt({ type: 'keyboard-toggle', enabled: enabled }));
    }
  }

  getStatus() {
    return {
      pairingCode: this.pairingCode,
      keyboardEnabled: this.keyboardEnabled,
      encrypted: this.encrypted
    };
  }
}

// Setup WebSocket connections
wss.on('connection', (ws, req) => {
  const url = new URL(req.url, 'http://localhost');
  const role = url.searchParams.get('role') || 'viewer';
  const pairingCode = url.searchParams.get('pairingCode');
  
  ws.role = role;
  console.log(`Client connected as ${role}, pairingCode: ${pairingCode || 'N/A'}`);

  // Handle pairing code generation and connection
  if (pairingCode) {
    let room = pairingCodes.get(pairingCode);
    if (!room) {
      room = new PairRoom(pairingCode);
      pairingCodes.set(pairingCode, room);
      console.log(`Created new pair room: ${pairingCode}`);
    }

    if (role === 'pc') {
      room.addPCSocket(ws);
    } else if (role === 'mobile') {
      room.addMobileSocket(ws);
    }

    connections.set(ws, room);

    // Send room status to connected device
    ws.send(JSON.stringify({
      type: 'info',
      message: `Connected as ${role} to pair ${pairingCode}`,
      status: room.getStatus()
    }));

    // Check if pair is complete
    if (room.pcSocket && room.mobileSocket) {
      const status = room.getStatus();
      if (room.pcSocket.readyState === WebSocket.OPEN) {
        room.pcSocket.send(JSON.stringify({
          type: 'pair-complete',
          message: 'Pair established successfully',
          status: status
        }));
      }
      if (room.mobileSocket.readyState === WebSocket.OPEN) {
        room.mobileSocket.send(JSON.stringify({
          type: 'pair-complete',
          message: 'Pair established successfully',
          status: status
        }));
      }
      console.log(`Pair ${pairingCode} established: both devices connected`);
    }
  } else {
    // Legacy mode for backward compatibility
    if (role === 'pc') {
      // Keep backward compatibility - store legacy PC socket
    } else if (role === 'mobile') {
      // Keep backward compatibility - store legacy mobile socket
    }
    
    connections.set(ws, null); // No room for standalone connections
  }

  ws.on('message', (data) => {
    try {
      const room = connections.get(ws);
      if (!room) return;

      // Handle encryption if room is encrypted
      let messageData;
      if (room.encrypted) {
        messageData = room.decrypt(data.toString());
      } else {
        messageData = JSON.parse(data.toString());
      }

      if (!messageData) return;

      // Route message based on type
      switch (messageData.type) {
        case 'key':
          if (ws.role === 'mobile') {
            room.forwardKeyboardFromMobile(data.toString());
          }
          break;

        case 'clipboard-set':
          if (ws.role === 'pc') {
            room.forwardClipboard(messageData.data);
          }
          break;

        case 'keyboard-toggle':
          if (ws.role === 'pc' && messageData.enabled !== undefined) {
            room.keyboardEnabled = messageData.enabled;
            room.sendKeyboardToggle('mobile', messageData.enabled);
          }
          break;
      }
    } catch (e) {
      console.log('Message handling error:', e.message);
    }
  });

  ws.on('close', () => {
    const room = connections.get(ws);
    if (room) {
      if (ws.role === 'pc' && room.pcSocket === ws) {
        room.pcSocket = null;
      } else if (ws.role === 'mobile' && room.mobileSocket === ws) {
        room.mobileSocket = null;
      }
      connections.delete(ws);
      console.log(`Client disconnected from pair ${room.pairingCode || 'unknown'}`);
    } else {
      connections.delete(ws);
    }
  });
});

// API endpoints

// Generate pairing code
app.post('/api/pairing/generate', express.json(), (req, res) => {
  const code = generatePairingCode();
  const room = new PairRoom(code);
  pairingCodes.set(code, room);
  res.json({ pairingCode: code });
});

// Check pairing status
app.get('/api/pairing/:code', (req, res) => {
  const room = pairingCodes.get(req.params.code);
  if (room) {
    res.json({
      status: 'active',
      keyboardEnabled: room.keyboardEnabled,
      encrypted: room.encrypted
    });
  } else {
    res.status(404).json({ error: 'Pairing code not found' });
  }
});

// Toggle keyboard remote control
app.post('/api/keyboard/toggle', express.json(), (req, res) => {
  const { pairingCode, enabled } = req.body;
  const room = pairingCodes.get(pairingCode);
  if (room) {
    room.keyboardEnabled = enabled;
    room.sendKeyboardToggle(enabled ? 'mobile' : 'pc', enabled);
    res.json({ ok: true, keyboardEnabled: room.keyboardEnabled });
  } else {
    res.status(404).json({ error: 'Pairing code not found' });
  }
});

// Get clipboard data
app.get('/api/clipboard', (req, res) => {
  const pairingCode = req.query.pairingCode;
  const room = pairingCodes.get(pairingCode);
  if (room && room.pcSocket) {
    res.json({ status: 'ready', message: 'PC clipboard access endpoint' });
  } else {
    res.status(404).json({ error: 'Pairing code not found or PC not connected' });
  }
});

// Set clipboard data (encrypted)
app.post('/api/clipboard', express.json(), (req, res) => {
  const { pairingCode, data } = req.body;
  const room = pairingCodes.get(pairingCode);
  if (room) {
    room.forwardClipboard(data);
    res.json({ ok: true });
  } else {
    res.status(404).json({ error: 'Pairing code not found' });
  }
});

// Legacy PC type endpoint (for backward compatibility)
app.post('/type', express.json(), (req, res) => {
  const { text } = req.body;
  exec(`xdotool type --clearmodifiers '${text.replace(/'/g, "'\''")}'`, (err) => {
    if (err) return res.status(500).send(err.message);
    res.send({ ok: true });
  });
});

const PORT = process.env.PORT || 3000;
server.listen(PORT, '0.0.0.0', () => {
  console.log(`Keyboard sync server running on http://0.0.0.0:${PORT}`);
  console.log('Mobile:  http://<host>:3000/?role=mobile');
  console.log('PC:      http://<host>:3000/?role=pc');
  console.log('Pairing: POST /api/pairing/generate');
});
