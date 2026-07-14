import { app, BrowserWindow, screen, ipcMain } from 'electron'
import * as path from 'path'
import { BackendManager } from './backend'
import { activateLicense, checkLicense, getLicenseInfo } from './license'

let mainWindow: BrowserWindow | null = null
const backend = new BackendManager()

function createWindow(): void {
  const { width: screenW, height: screenH } = screen.getPrimaryDisplay().workAreaSize

  mainWindow = new BrowserWindow({
    width: Math.min(1400, screenW),
    height: Math.min(900, screenH),
    minWidth: 1024,
    minHeight: 680,
    title: 'Mipham Quant',
    icon: path.join(__dirname, '..', 'resources', 'icon.png'),
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      contextIsolation: true,
      nodeIntegration: false,
    },
    // macOS: hide instead of close
    ...(process.platform === 'darwin'
      ? { titleBarStyle: 'hiddenInset' }
      : {}),
  })

  // Load frontend
  const isDev = process.env.NODE_ENV === 'development'
  if (isDev) {
    mainWindow.loadURL('http://localhost:5173')
    mainWindow.webContents.openDevTools()
  } else {
    mainWindow.loadFile(path.join(__dirname, '..', 'frontend', 'dist', 'index.html'))
  }

  mainWindow.on('closed', () => {
    mainWindow = null
  })
}

// Start backend before creating window
async function bootstrap(): Promise<void> {
  try {
    await backend.start()
  } catch (err) {
    console.error('Failed to start backend:', err)
    // Show error in window later
  }

  createWindow()

  // IPC handlers
  ipcMain.handle('backend:status', () => backend.isReady)
  ipcMain.handle('app:getVersion', () => app.getVersion())
  ipcMain.handle('app:getPlatform', () => process.platform)

  // License IPC handlers
  ipcMain.handle('license:activate', (_event, key: string) => {
    return activateLicense(key)
  })
  ipcMain.handle('license:status', () => {
    return {
      activated: checkLicense(),
      info: getLicenseInfo(),
    }
  })
}

app.whenReady().then(bootstrap)

app.on('before-quit', async () => {
  await backend.stop()
})

app.on('window-all-closed', () => {
  // Don't quit on window close — keep running in tray (Task 9)
})

app.on('activate', () => {
  if (BrowserWindow.getAllWindows().length === 0) {
    createWindow()
  }
})
