// shared/src/utils.ts
import { v4 as uuidv4 } from 'uuid';
import { ConnectionStatus, DevicePair, ClipboardData } from './types';

export class ConnectionManager {
  private connections = new Map<string, ConnectionStatus>();
  private pairs = new Map<string, DevicePair>();
  private clipboardHistory: ClipboardData[] = [];

  generatePairingCode(): string {
    return Math.floor(100000 + Math.random() * 900000).toString();
  }

  createPair(pairingCode: string): DevicePair {
    const pair: DevicePair = {
      pairingCode,
      pcConnected: false,
      mobileConnected: false,
      keyboardEnabled: true,
      lastActivity: Date.now()
    };
    this.pairs.set(pairingCode, pair);
    return pair;
  }

  getPair(pairingCode: string): DevicePair | undefined {
    return this.pairs.get(pairingCode);
  }

  updateConnection(pairingCode: string, role: 'pc' | 'mobile', isConnected: boolean): ConnectionStatus {
    const existing = this.connections.get(pairingCode) || {
      pairingCode,
      role,
      isConnected: false,
      keyboardEnabled: true,
      lastSeen: 0
    };

    const status: ConnectionStatus = {
      ...existing,
      role,
      isConnected,
      lastSeen: isConnected ? Date.now() : existing.lastSeen
    };

    this.connections.set(pairingCode, status);

    // Update pair status
    const pair = this.getPair(pairingCode);
    if (pair) {
      if (role === 'pc') pair.pcConnected = isConnected;
      if (role === 'mobile') pair.mobileConnected = isConnected;
      pair.lastActivity = Date.now();
    }

    return status;
  }

  addClipboardData(data: Omit<ClipboardData, 'timestamp'>): void {
    const clipboardData: ClipboardData = {
      ...data,
      timestamp: Date.now()
    };
    this.clipboardHistory.push(clipboardData);
    // Keep only last 100 items
    if (this.clipboardHistory.length > 100) {
      this.clipboardHistory = this.clipboardHistory.slice(-100);
    }
  }

  getRecentClipboard(pairingCode: string, limit: number = 5): ClipboardData[] {
    return this.clipboardHistory
      .filter(item => item.source === pairingCode)
      .slice(-limit);
  }

  getAllConnections(): ConnectionStatus[] {
    return Array.from(this.connections.values());
  }

  getActivePairs(): DevicePair[] {
    return Array.from(this.pairs.values());
  }
}
