// server/tests/websocket.test.ts
import { WebSocketManager } from '../src/websocket';

describe('WebSocketManager', () => {
  let webSocketManager: WebSocketManager;

  beforeEach(() => {
    webSocketManager = new WebSocketManager();
  });

  describe('createRoom', () => {
    it('should create a new room with pairing code', () => {
      const pairingCode = '123456';
      const room = webSocketManager.createRoom(pairingCode);

      expect(room.pairingCode).toBe(pairingCode);
      expect(room.pcSocket).toBeNull();
      expect(room.mobileSocket).toBeNull();
      expect(room.keyboardEnabled).toBe(true);
    });

    it('should return existing room when created twice', () => {
      const pairingCode = '123456';
      const room1 = webSocketManager.createRoom(pairingCode);
      const room2 = webSocketManager.createRoom(pairingCode);

      expect(room1).toBe(room2);
    });
  });

  describe('getRoom', () => {
    it('should return undefined for non-existent room', () => {
      const result = webSocketManager.getRoom('999999');
      expect(result).toBeUndefined();
    });

    it('should return existing room', () => {
      const pairingCode = '123456';
      const room = webSocketManager.createRoom(pairingCode);
      const result = webSocketManager.getRoom(pairingCode);

      expect(result).toBe(room);
    });
  });

  describe('getRoomStatus', () => {
    it('should return status for existing room', () => {
      const pairingCode = '123456';
      webSocketManager.createRoom(pairingCode);
      const status = webSocketManager.getRoomStatus(pairingCode);

      expect(status).toBeDefined();
      expect(status?.pairingCode).toBe(pairingCode);
      expect(status?.hasPCSocket).toBe(false);
      expect(status?.hasMobileSocket).toBe(false);
    });

    it('should return null for non-existent room', () => {
      const result = webSocketManager.getRoomStatus('999999');
      expect(result).toBeNull();
    });
  });
});
