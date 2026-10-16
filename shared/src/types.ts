// shared/src/types.ts
export interface WebSocketMessage {
  type: 'key' | 'clipboard-set' | 'keyboard-toggle' | 'pair-complete' | 'info';
  data?: any;
  timestamp?: number;
  pairingCode?: string;
  key?: string;
  enabled?: boolean;
}

export interface ConnectionStatus {
  pairingCode: string;
  role: 'pc' | 'mobile' | 'viewer';
  isConnected: boolean;
  keyboardEnabled: boolean;
  lastSeen: number;
}

export interface ClipboardData {
  content: string;
  timestamp: number;
  source: 'pc' | 'mobile';
}

export interface DevicePair {
  pairingCode: string;
  pcConnected: boolean;
  mobileConnected: boolean;
  keyboardEnabled: boolean;
  lastActivity: number;
}

export interface ApiResponse<T = any> {
  success: boolean;
  data?: T;
  error?: string;
  message?: string;
}
