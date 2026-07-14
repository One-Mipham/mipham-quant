import { spawn, ChildProcess } from 'child_process'
import * as path from 'path'
import * as http from 'http'
import { app } from 'electron'

const BACKEND_PORT = 5000
const HEALTH_URL = `http://127.0.0.1:${BACKEND_PORT}/api/health`
const MAX_RETRIES = 3
const HEALTH_POLL_MS = 500
const HEALTH_TIMEOUT_MS = 30000

export class BackendManager {
  private process: ChildProcess | null = null
  private crashCount = 0
  private _ready = false

  get isReady(): boolean {
    return this._ready
  }

  async start(): Promise<void> {
    if (this.process) return

    const isDev = process.env.NODE_ENV === 'development'
    const userDataPath = app.getPath('userData')

    let cmd: string
    let args: string[]

    if (isDev) {
      cmd = 'python3'
      args = [path.join(__dirname, '..', 'backend_api_python', 'run.py')]
    } else {
      // Production: PyInstaller binary in extraResources
      const backendDir = path.join(process.resourcesPath, 'backend')
      if (process.platform === 'win32') {
        cmd = path.join(backendDir, 'mipham-quant-backend.exe')
      } else {
        cmd = path.join(backendDir, 'mipham-quant-backend')
      }
      args = []
    }

    const env = {
      ...process.env,
      DB_TYPE: 'sqlite',
      DB_PATH: path.join(userDataPath, 'quant.db'),
      PYTHON_API_HOST: '127.0.0.1',
      PYTHON_API_PORT: String(BACKEND_PORT),
      PYTHON_API_DEBUG: isDev ? 'true' : 'false',
      SINGLE_USER_MODE: 'true',
      ENABLE_CACHE: 'false',
      ENABLE_REGISTRATION: 'false',
      // Bypass proxy for local
      PROXY_URL: '',
      // Generate a local SECRET_KEY if not already set
      SECRET_KEY: process.env.SECRET_KEY || require('crypto').randomBytes(32).toString('hex'),
    }

    console.log(`[Backend] Starting: ${cmd} ${args.join(' ')}`)
    console.log(`[Backend] DB_PATH: ${env.DB_PATH}`)

    this.process = spawn(cmd, args, {
      env,
      stdio: ['ignore', 'pipe', 'pipe'],
    })

    this.process.stdout?.on('data', (data: Buffer) => {
      console.log(`[Backend] ${data.toString().trim()}`)
    })

    this.process.stderr?.on('data', (data: Buffer) => {
      console.error(`[Backend:err] ${data.toString().trim()}`)
    })

    this.process.on('exit', (code, signal) => {
      console.log(`[Backend] Process exited: code=${code} signal=${signal}`)
      this._ready = false
      if (code !== 0 && code !== null) {
        this.crashCount++
        if (this.crashCount < MAX_RETRIES) {
          console.log(`[Backend] Auto-restart attempt ${this.crashCount}/${MAX_RETRIES}`)
          setTimeout(() => this.start(), 2000)
        }
      }
    })

    // Wait for backend to be healthy
    await this._waitForHealth()
  }

  async stop(): Promise<void> {
    if (!this.process) return

    return new Promise((resolve) => {
      const timeout = setTimeout(() => {
        if (this.process) {
          console.log('[Backend] Force kill after timeout')
          this.process.kill('SIGKILL')
        }
        resolve()
      }, 5000)

      this.process!.on('exit', () => {
        clearTimeout(timeout)
        this.process = null
        this._ready = false
        resolve()
      })

      this.process!.kill('SIGTERM')
    })
  }

  async restart(): Promise<void> {
    await this.stop()
    this.crashCount = 0
    await this.start()
  }

  private _waitForHealth(): Promise<void> {
    return new Promise((resolve, reject) => {
      const startTime = Date.now()

      const poll = () => {
        if (Date.now() - startTime > HEALTH_TIMEOUT_MS) {
          reject(new Error('Backend health check timed out'))
          return
        }

        http.get(HEALTH_URL, (res) => {
          if (res.statusCode === 200) {
            this._ready = true
            this.crashCount = 0
            console.log('[Backend] Ready!')
            resolve()
          } else {
            setTimeout(poll, HEALTH_POLL_MS)
          }
        }).on('error', () => {
          setTimeout(poll, HEALTH_POLL_MS)
        })
      }

      poll()
    })
  }
}
