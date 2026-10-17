// server/tests/api.test.ts
import request from 'supertest';
import express from 'express';
import { WebSocketManager } from '../src/websocket';
import { ApiServer } from '../src/api';

describe('API Server', () => {
  let app: express.Application;
  let webSocketManager: WebSocketManager;

  beforeEach(() => {
    webSocketManager = new WebSocketManager();
    const apiServer = new ApiServer(webSocketManager);
    app = apiServer.getApp();
  });

  describe('POST /api/pairing/generate', () => {
    it('should generate a pairing code', async () => {
      const response = await request(app)
        .post('/api/pairing/generate')
        .expect(200);

      expect(response.body).toHaveProperty('pairingCode');
      expect(typeof response.body.pairingCode).toBe('string');
      expect(response.body.pairingCode).toMatch(/^\d{6}$/);
    });
  });

  describe('GET /api/pairing/:code', () => {
    it('should return room status for existing pairing code', async () => {
      const pairingCode = '123456';
      webSocketManager.createRoom(pairingCode);

      const response = await request(app)
        .get(`/api/pairing/${pairingCode}`)
        .expect(200);

      expect(response.body).toHaveProperty('pairingCode');
      expect(response.body.pairingCode).toBe(pairingCode);
    });

    it('should return 404 for non-existent pairing code', async () => {
      const response = await request(app)
        .get('/api/pairing/999999')
        .expect(404);

      expect(response.body).toHaveProperty('error');
    });
  });

  describe('POST /api/keyboard/toggle', () => {
    it('should toggle keyboard enabled state', async () => {
      const pairingCode = '123456';
      webSocketManager.createRoom(pairingCode);

      const response = await request(app)
        .post('/api/keyboard/toggle')
        .send({ pairingCode, enabled: false })
        .expect(200);

      expect(response.body).toHaveProperty('ok', true);
      expect(response.body.keyboardEnabled).toBe(false);
    });
  });

  describe('GET /health', () => {
    it('should return health status', async () => {
      const response = await request(app)
        .get('/health')
        .expect(200);

      expect(response.body).toHaveProperty('status', 'ok');
      expect(response.body).toHaveProperty('activeConnections');
      expect(response.body).toHaveProperty('timestamp');
    });
  });
});
