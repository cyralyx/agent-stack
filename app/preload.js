'use strict';
// preload.js — secure context bridge (contextIsolation on, nodeIntegration off).
const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('agentstack', {
  status: () => ipcRenderer.invoke('system:status'),
  open: (target) => ipcRenderer.invoke('system:open', target),
  openExternal: (url) => ipcRenderer.invoke('system:openExternal', url),

  ask: (prompt, model) => ipcRenderer.invoke('app:ask', prompt, model),
  council: (prompt) => ipcRenderer.invoke('app:council', prompt),

  tasks: {
    list: () => ipcRenderer.invoke('tasks:list'),
    add: (title, extra) => ipcRenderer.invoke('tasks:add', title, extra),
    complete: (id) => ipcRenderer.invoke('tasks:complete', id),
    reopen: (id) => ipcRenderer.invoke('tasks:reopen', id),
    remove: (id) => ipcRenderer.invoke('tasks:remove', id),
    export: () => ipcRenderer.invoke('tasks:export'),
  },

  notes: {
    add: (text) => ipcRenderer.invoke('notes:add', text),
  },

  providers: {
    list: () => ipcRenderer.invoke('providers:list'),
    status: () => ipcRenderer.invoke('providers:status'),
  },

  perms: {
    list: () => ipcRenderer.invoke('perms:list'),
    audit: () => ipcRenderer.invoke('perms:audit'),
  },

  security: {
    scan: () => ipcRenderer.invoke('security:scan'),
  },

  cost: {
    report: (days) => ipcRenderer.invoke('cost:report', days),
  },

  events: {
    recent: () => ipcRenderer.invoke('events:recent'),
  },
});
