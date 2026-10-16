// desktop/src/preload/preload.ts
electron.ipcRenderer.on('api-response', (event, data) => {
  window.postMessage({ type: 'api-response', data });
});

window.addEventListener('message', (event) => {
  if (event.data.type === 'api-request') {
    electron.ipcRenderer.send('api-request', event.data.payload);
  }
});
