// mobile/src/services/apiService.ts
import axios from 'axios';
import { CONSTANTS } from '@/shared/constants';
import { DevicePair, ApiResponse, ClipboardData } from '@/shared/types';

const API_BASE_URL = CONSTANTS.API.BASE_URL;

export class ApiService {
  private baseURL = '';

  constructor() {
    if (__DEV__) {
      this.baseURL = 'http://localhost:3000';
    } else {
      this.baseURL = 'https://your-server.com';
    }
  }

  async generatePairingCode(): Promise<ApiResponse<{ pairingCode: string }>> {
    try {
      const response = await axios.post(`${this.baseURL}${CONSTANTS.API.ENDPOINTS.PAIRING_GENERATE}`);
      return { success: true, data: response.data };
    } catch (error) {
      return { success: false, error: 'Failed to generate pairing code' };
    }
  }

  async getPairingStatus(pairingCode: string): Promise<ApiResponse<DevicePair>> {
    try {
      const response = await axios.get(`${this.baseURL}${CONSTANTS.API.ENDPOINTS.PAIRING_STATUS.replace(':code', pairingCode)}`);
      return { success: true, data: response.data };
    } catch (error) {
      return { success: false, error: 'Failed to get pairing status' };
    }
  }

  async toggleKeyboard(pairingCode: string, enabled: boolean): Promise<ApiResponse> {
    try {
      const response = await axios.post(`${this.baseURL}${CONSTANTS.API.ENDPOINTS.KEYBOARD_TOGGLE}`, {
        pairingCode,
        enabled
      });
      return { success: true, data: response.data };
    } catch (error) {
      return { success: false, error: 'Failed to toggle keyboard' };
    }
  }

  async setClipboard(pairingCode: string, data: string): Promise<ApiResponse> {
    try {
      const response = await axios.post(`${this.baseURL}${CONSTANTS.API.ENDPOINTS.CLIPBOARD_SET}`, {
        pairingCode,
        data
      });
      return { success: true, data: response.data };
    } catch (error) {
      return { success: false, error: 'Failed to set clipboard' };
    }
  }

  async getHealthStatus(): Promise<ApiResponse> {
    try {
      const response = await axios.get(`${this.baseURL}${CONSTANTS.API.HEALTH_CHECK}`);
      return { success: true, data: response.data };
    } catch (error) {
      return { success: false, error: 'Health check failed' };
    }
  }
}
