// server/src/api.ts
import express from 'express';
import { WebSocketManager } from './websocket';

export class ApiServer {
  private app = express();
  private webSocketManager: WebSocketManager;
  private wss: any;

  constructor(webSocketManager: WebSocketManager) {
    this.webSocketManager = webSocketManager;
    this.setupMiddleware();
    this.setupRoutes();
  }

  private setupMiddleware(): void {
    this.app.use(express.json());
  }

  private setupRoutes(): void {
    // Generate pairing code
    this.app.post('/api/pairing/generate', (req, res) => {
      const pairingCode = this.generatePairingCode();
      this.webSocketManager.createRoom(pairingCode);
      res.json({ pairingCode });
    });

    // Check pairing status
    this.app.get('/api/pairing/:code', (req, res) => {
      const status = this.webSocketManager.getRoomStatus(req.params.code);
      if (status) {
        res.json(status);
      } else {
        res.status(404).json({ error: 'Pairing code not found' });
      }
    });

    // Toggle keyboard remote control
    this.app.post('/api/keyboard/toggle', (req, res) => {
      const { pairingCode, enabled } = req.body;
      const room = this.webSocketManager.getRoom(pairingCode);
      if (room) {
        room.keyboardEnabled = enabled;
        this.webSocketManager.sendKeyboardToggle(room, 'mobile', enabled);
        this.webSocketManager.sendKeyboardToggle(room, 'pc', enabled);
        res.json({ ok: true, keyboardEnabled: room.keyboardEnabled });
      } else {
        res.status(404).json({ error: 'Pairing code not found' });
      }
    });

    // Get clipboard data endpoint (for status check)
    this.app.get('/api/clipboard', (req, res) => {
      const pairingCode = req.query.pairingCode as string;
      const room = this.webSocketManager.getRoom(pairingCode);
      if (room && room.pcSocket) {
        res.json({ status: 'ready', message: 'PC clipboard access endpoint' });
      } else {
        res.status(404).json({ error: 'Pairing code not found or PC not connected' });
      }
    });

    // Set clipboard data (encrypted)
    this.app.post('/api/clipboard', (req, res) => {
      const { pairingCode, data } = req.body;
      const room = this.webSocketManager.getRoom(pairingCode);
      if (room) {
        this.webSocketManager.forwardClipboard(room, data);
        res.json({ ok: true });
      } else {
        res.status(404).json({ error: 'Pairing code not found' });
      }
    });

    // Health check endpoint
    this.app.get('/health', (req, res) => {
      res.json({ 
        status: 'ok', 
        activeConnections: this.webSocketManager.getActiveConnections(),
        timestamp: new Date().toISOString()
      });
    });
  }

  private generatePairingCode(): string {
    return Math.floor(100000 + Math.random() * 900000).toString();
  }

  public start(port: number = 3000): void {
    this.app.listen(port, '0.0.0.0', () => {
      console.log(`Keyboard sync server running on http://0.0.0.0:${port}`);
      console.log(`Pairing: POST /api/pairing/generate`);
    });
  }

  public getApp() {
    return this.app;
  }
}
