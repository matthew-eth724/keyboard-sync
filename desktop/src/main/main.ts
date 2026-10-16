// desktop/src/main/main.ts
import { app, BrowserWindow, ipcMain } from 'electron';
import * as path from 'path';
import { fileURLToPath } from 'url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));

let mainWindow: BrowserWindow | null = null;

app.whenReady().then(() => {
  mainWindow = new BrowserWindow({
    width: 900,
    height: 700,
    webPreferences: {
      preload: path.join(__dirname, 'preload/preload.ts'),
      nodeIntegration: false,
      contextIsolation: true,
      webSecurity: true
    }
  });

  mainWindow.loadFile(path.join(__dirname, '../renderer/index.html'));

  mainWindow.on('closed', () => {
    mainWindow = null;
  });
});

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') {
    app.quit();
  }
});

ipcMain.handle('api-request', async (event, payload) => {
  const { action, data } = payload;
  
  // Handle API requests
  switch (action) {
    case 'generate-pairing':
      // TODO: Implement API call to server
      return { success: true, pairingCode: '123456' };
    case 'get-pairing-status':
      return { success: true, status: { keyboardEnabled: true } };
    case 'toggle-keyboard':
      return { success: true, keyboardEnabled: data.enabled };
    case 'get-clipboard':
      return { success: true, data: 'clipboard content' };
    case 'set-clipboard':
      return { success: true };
    default:
      return { success: false, error: 'Unknown action' };
  }
});
