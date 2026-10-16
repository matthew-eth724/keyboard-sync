// shared/src/constants.ts
export const CONSTANTS = {
  API: {
    BASE_URL: '/api',
    ENDPOINTS: {
      PAIRING_GENERATE: '/api/pairing/generate',
      PAIRING_STATUS: '/api/pairing/:code',
      KEYBOARD_TOGGLE: '/api/keyboard/toggle',
      CLIPBOARD_GET: '/api/clipboard',
      CLIPBOARD_SET: '/api/clipboard'
    },
    HEALTH_CHECK: '/health'
  },
  WEBSOCKET: {
    EVENTS: {
      CONNECTION: 'connection',
      MESSAGE: 'message',
      DISCONNECT: 'close',
      ERROR: 'error'
    },
    ROLES: {
      PC: 'pc',
      MOBILE: 'mobile',
      VIEWER: 'viewer'
    }
  },
  UI: {
    ANIMATION_DURATION: 300,
    DEBOUNCE_DELAY: 300,
    KEYBOARD_ROWS: ['qwertyuiop', 'asdfghjkl', 'zxcvbnm']
  },
  STORAGE: {
    KEYBOARD_TOGGLE_KEY: 'keyboard-toggle-enabled',
    LAST_PAIRING_CODE: 'last-pairing-code'
  }
};
