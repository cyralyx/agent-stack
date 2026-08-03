'use strict';
// AgentStack — preload bridge (contextIsolation safe).
const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('agentstack', {
  status: () => ipcRenderer.invoke('system:status'),
  open: (target) => ipcRenderer.invoke('system:open', target),
  openExternal: (url) => ipcRenderer.invoke('system:openExternal', url),
  ask: (prompt) => ipcRenderer.invoke('app:ask', prompt),
  council: (prompt) => ipcRenderer.invoke('app:council', prompt),
  todo: (action, arg) => ipcRenderer.invoke('app:todo', action, arg),
});
