import { contextBridge, ipcRenderer } from 'electron'

// Expose minimal, safe API to the renderer process.
// All communication goes through IPC — no direct Node.js access.
contextBridge.exposeInMainWorld('electronAPI', {
  // App info
  getVersion: () => ipcRenderer.invoke('app:getVersion'),
  getPlatform: () => process.platform,

  // License
  activateLicense: (key: string) => ipcRenderer.invoke('license:activate', key),
  getLicenseStatus: () => ipcRenderer.invoke('license:status'),

  // Backend status
  getBackendStatus: () => ipcRenderer.invoke('backend:status'),

  // Notifications
  onBackendReady: (callback: () => void) => {
    ipcRenderer.on('backend:ready', callback)
  },
  onBackendError: (callback: (msg: string) => void) => {
    ipcRenderer.on('backend:error', (_event, msg) => callback(msg))
  },
})
