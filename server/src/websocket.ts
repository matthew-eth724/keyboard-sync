// server/src/websocket.ts
import { WebSocket } from 'ws';
import { EncryptionService } from './encryption';

export interface WebSocketMessage {
  type: string;
  data?: any;
  timestamp?: number;
  pairingCode?: string;
}

export interface PairRoom {
  pairingCode: string;
  pcSocket: WebSocket | null;
  mobileSocket: WebSocket | null;
  encryption: EncryptionService;
  keyboardEnabled: boolean;
  connectionTime: number;
}

export class WebSocketManager {
  private rooms = new Map<string, PairRoom>();
  private connections = new Map<WebSocket, string>();
  private encryptionService: EncryptionService;

  constructor() {
    this.encryptionService = new EncryptionService();
  }

  createRoom(pairingCode: string): PairRoom {
    const room: PairRoom = {
      pairingCode,
      pcSocket: null,
      mobileSocket: null,
      encryption: new EncryptionService(),
      keyboardEnabled: true,
      connectionTime: Date.now()
    };
    this.rooms.set(pairingCode, room);
    return room;
  }

  getRoom(pairingCode: string): PairRoom | undefined {
    return this.rooms.get(pairingCode);
  }

  addPCSocket(pairingCode: string, socket: WebSocket): void {
    let room = this.getRoom(pairingCode);
    if (!room) {
      room = this.createRoom(pairingCode);
    }
    room.pcSocket = socket;
    socket.pairingCode = pairingCode;
    this.connections.set(socket, pairingCode);
  }

  addMobileSocket(pairingCode: string, socket: WebSocket): void {
    let room = this.getRoom(pairingCode);
    if (!room) {
      room = this.createRoom(pairingCode);
    }
    room.mobileSocket = socket;
    socket.pairingCode = pairingCode;
    this.connections.set(socket, pairingCode);
  }

  forwardKeyboardFromMobile(room: PairRoom, data: string): void {
    if (!room.keyboardEnabled) return;
    
    const decrypted = room.encryption.decrypt(data);
    if (decrypted && decrypted.type === 'key' && room.pcSocket?.readyState === WebSocket.OPEN) {
      const encrypted = room.encryption.encrypt(decrypted);
      room.pcSocket.send(encrypted);
    }
  }

  forwardClipboard(room: PairRoom, data: any): void {
    if (room.mobileSocket?.readyState === WebSocket.OPEN) {
      const message = room.encryption.encrypt({ type: 'clipboard', data });
      room.mobileSocket.send(message);
    }
  }

  sendKeyboardToggle(room: PairRoom, to: 'mobile' | 'pc', enabled: boolean): void {
    const targetSocket = to === 'mobile' ? room.mobileSocket : room.pcSocket;
    if (targetSocket?.readyState === WebSocket.OPEN) {
      const message = room.encryption.encrypt({ type: 'keyboard-toggle', enabled });
      targetSocket.send(message);
    }
  }

  getRoomStatus(pairingCode: string): any {
    const room = this.getRoom(pairingCode);
    if (!room) return null;
    
    return {
      pairingCode: room.pairingCode,
      keyboardEnabled: room.keyboardEnabled,
      hasPCSocket: !!room.pcSocket,
      hasMobileSocket: !!room.mobileSocket,
      connectionTime: room.connectionTime
    };
  }

  removeSocket(socket: WebSocket): void {
    const pairingCode = this.connections.get(socket);
    if (pairingCode) {
      const room = this.getRoom(pairingCode);
      if (room) {
        if (room.pcSocket === socket) room.pcSocket = null;
        if (room.mobileSocket === socket) room.mobileSocket = null;
      }
      this.connections.delete(socket);
    }
  }

  getActiveConnections(): number {
    return this.connections.size;
  }
}
