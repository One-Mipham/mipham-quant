import { app, BrowserWindow, screen, ipcMain } from 'electron'
import * as path from 'path'
import { BackendManager } from './backend'
import { activateLicense, checkLicense, getLicenseInfo, isActivated } from './license'
import { createTray, showNotification } from './tray'

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

  // Close = hide to tray (not quit)
  mainWindow.on('close', (event) => {
    if (!(app as any).isQuitting) {
      event.preventDefault()
      mainWindow!.hide()
      showNotification('Mipham Quant', '应用已最小化到系统托盘，策略继续运行中。')
    }
  })

  mainWindow.on('closed', () => {
    mainWindow = null
  })
}

async function bootstrap(): Promise<void> {
  // Register IPC handlers (always available)
  ipcMain.handle('backend:status', () => backend.isReady)
  ipcMain.handle('app:getVersion', () => app.getVersion())
  ipcMain.handle('app:getPlatform', () => process.platform)

  // License IPC handlers (always available for activation flow)
  ipcMain.handle('license:activate', (_event, key: string) => {
    return activateLicense(key)
  })
  ipcMain.handle('license:status', () => {
    return {
      activated: checkLicense(),
      info: getLicenseInfo(),
    }
  })

  // Forward tray commands to renderer
  ipcMain.on('tray:pauseAll', () => {
    showNotification('Mipham Quant', '所有策略已暂停')
  })

  ipcMain.on('tray:resumeAll', () => {
    showNotification('Mipham Quant', '所有策略已恢复')
  })

  // Check license before starting backend
  if (!isActivated()) {
    // Show activation dialog
    createWindow()
    mainWindow?.webContents.on('did-finish-load', () => {
      mainWindow?.webContents.send('license:required')
    })
    return
  }

  // Start backend and show main window
  try {
    await backend.start()
  } catch (err) {
    console.error('Failed to start backend:', err)
  }
  createWindow()

  // Create system tray
  createTray(mainWindow!)

  // Notify renderer when backend is ready
  if (mainWindow) {
    mainWindow.webContents.send('backend:ready')
  }
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
