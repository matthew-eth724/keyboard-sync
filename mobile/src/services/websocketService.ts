// mobile/src/services/websocketService.ts
import { Socket, io } from 'socket.io-client';
import { WebSocketMessage, ConnectionStatus, ApiResponse } from '@/shared/types';
import { CONSTANTS } from '@/shared/constants';

export class WebSocketService {
  private socket: Socket | null = null;
  private pairingCode: string | null = null;
  private role: 'pc' | 'mobile' = 'mobile';
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 5;
  private reconnectTimeout?: NodeJS.Timeout;

  constructor() {}

  connect(role: 'pc' | 'mobile', pairingCode: string): void {
    this.role = role;
    this.pairingCode = pairingCode;
    
    const wsUrl = `${CONSTANTS.API.BASE_URL}?role=${role}&pairingCode=${pairingCode}`;
    this.socket = io(wsUrl, {
      transports: ['websocket'],
      reconnection: true,
      reconnectionAttempts: this.maxReconnectAttempts,
      timeout: 20000
    });

    this.setupEventListeners();
  }

  private setupEventListeners(): void {
    if (!this.socket) return;

    this.socket.on('connect', () => {
      console.log('Connected to keyboard sync server');
      this.reconnectAttempts = 0;
    });

    this.socket.on('disconnect', () => {
      console.log('Disconnected from keyboard sync server');
      this.handleReconnect();
    });

    this.socket.on('connect_error', (error) => {
      console.error('Connection error:', error);
      this.reconnectAttempts++;
    });

    this.socket.onAny((event, ...args) => {
      console.log(`Received ${event}:`, args);
    });
  }

  private handleReconnect(): void {
    if (this.reconnectAttempts < this.maxReconnectAttempts && this.pairingCode) {
      this.reconnectTimeout = setTimeout(() => {
        this.connect(this.role, this.pairingCode!);
      }, Math.min(1000 * Math.pow(2, this.reconnectAttempts), 30000));
    }
  }

  sendMessage(message: Partial<WebSocketMessage>): void {
    if (this.socket?.connected) {
      this.socket.emit('message', message);
    }
  }

  sendKey(key: string): void {
    this.sendMessage({ type: 'key', key, timestamp: Date.now() });
  }

  sendClipboard(data: string): void {
    this.sendMessage({ type: 'clipboard-set', data, timestamp: Date.now() });
  }

  toggleKeyboard(enabled: boolean): void {
    this.sendMessage({ type: 'keyboard-toggle', enabled, timestamp: Date.now() });
  }

  disconnect(): void {
    if (this.reconnectTimeout) {
      clearTimeout(this.reconnectTimeout);
    }
    if (this.socket) {
      this.socket.disconnect();
      this.socket = null;
    }
  }

  isConnected(): boolean {
    return this.socket?.connected || false;
  }

  getConnectionStatus(): ConnectionStatus | null {
    if (!this.socket?.connected || !this.pairingCode) {
      return null;
    }
    
    return {
      pairingCode: this.pairingCode,
      role: this.role,
      isConnected: true,
      keyboardEnabled: true, // TODO: get from server
      lastSeen: Date.now()
    };
  }
}
