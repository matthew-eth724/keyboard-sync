// server/tests/server.test.ts
import request from 'supertest';
import express from 'express';
import http from 'http';
import { WebSocketServer } from 'ws';
import { Server } from 'http';
import { WebSocketManager } from '../src/websocket';
import { ApiServer } from '../src/api';

describe('Keyboard Sync Server', () => {
  let server: Server;
  let app: express.Application;
  let webSocketManager: WebSocketManager;

  beforeAll(async () => {
    webSocketManager = new WebSocketManager();
    const apiServer = new ApiServer(webSocketManager);
    app = apiServer.getApp();

    server = http.createServer(app);
    server.listen(0); // Use random available port
  });

  afterAll((done) => {
    server.close(() => {
      done();
    });
  });

  describe('Server Initialization', () => {
    it('should start without errors', async () => {
      const port = (server.address() as any).port;
      const response = await request(app).get('/health').expect(200);
      expect(response.body.status).toBe('ok');
    });
  });
});
