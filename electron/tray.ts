import { Tray, Menu, nativeImage, app, BrowserWindow } from 'electron'
import * as path from 'path'

let tray: Tray | null = null

export function createTray(mainWindow: BrowserWindow): Tray {
  const iconPath = path.join(__dirname, '..', 'resources', 'icon.png')
  const icon = nativeImage.createFromPath(iconPath).resize({ width: 16, height: 16 })

  tray = new Tray(icon)
  tray.setToolTip('Mipham Quant')

  const updateMenu = () => {
    const contextMenu = Menu.buildFromTemplate([
      {
        label: '📊 显示主窗口',
        click: () => {
          mainWindow.show()
          mainWindow.focus()
        },
      },
      { type: 'separator' },
      {
        label: '⏸ 暂停所有策略',
        enabled: false, // Future: query backend for running strategies
        click: () => {
          mainWindow.webContents.send('tray:pauseAll')
        },
      },
      {
        label: '▶ 恢复所有策略',
        enabled: false,
        click: () => {
          mainWindow.webContents.send('tray:resumeAll')
        },
      },
      { type: 'separator' },
      {
        label: '⚙ 设置',
        click: () => {
          mainWindow.show()
          mainWindow.focus()
          mainWindow.webContents.send('nav:settings')
        },
      },
      {
        label: '❓ 关于',
        click: () => {
          const { dialog } = require('electron')
          dialog.showMessageBox(mainWindow, {
            type: 'info',
            title: '关于 Mipham Quant',
            message: 'Mipham Quant Desktop v1.0.0',
            detail: 'AI 量化交易平台\n\n©2026 One Mipham Corporation\n北京华安麦逄科技有限公司',
          })
        },
      },
      { type: 'separator' },
      {
        label: '✕ 退出',
        click: () => {
          ;(app as any).isQuitting = true
          app.quit()
        },
      },
    ])
    tray!.setContextMenu(contextMenu)
  }

  updateMenu()

  tray.on('double-click', () => {
    mainWindow.show()
    mainWindow.focus()
  })

  return tray
}

export function showNotification(title: string, body: string): void {
  const { Notification } = require('electron')
  if (Notification.isSupported()) {
    new Notification({ title, body, icon: path.join(__dirname, '..', 'resources', 'icon.png') }).show()
  }
}
