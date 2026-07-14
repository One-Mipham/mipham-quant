import * as crypto from 'crypto'
import * as fs from 'fs'
import * as path from 'path'
import { app } from 'electron'

// ⚠️  PUBLIC KEY ONLY — embedded in the app.
// The PRIVATE KEY stays with the license generator script (never shipped).
//
// GENERATE THE REAL KEY:
//   1. Run: python3 -c "
//      from cryptography.hazmat.primitives.asymmetric import rsa
//      from cryptography.hazmat.primitives import serialization
//      private = rsa.generate_private_key(65537, 2048)
//      with open('license_private.pem','wb') as f:
//          f.write(private.private_bytes(encoding=serialization.Encoding.PEM,
//              format=serialization.PrivateFormat.PKCS8,
//              encryption_algorithm=serialization.NoEncryption()))
//      print(private.public_key().public_bytes(
//          encoding=serialization.Encoding.PEM,
//          format=serialization.PublicFormat.SubjectPublicKeyInfo).decode())"
//   2. Copy the output (-----BEGIN PUBLIC KEY----- ... -----END PUBLIC KEY-----)
//   3. Paste it below, replacing this placeholder.
const PUBLIC_KEY_PEM = `-----BEGIN PUBLIC KEY-----
<PASTE THE REAL PUBLIC KEY HERE — SEE INSTRUCTIONS ABOVE>
-----END PUBLIC KEY-----`

interface LicensePayload {
  product: string
  email: string
  device_id?: string
  issued_at: string
  expires_at: string
  features: string[]
}

function getLicensePath(): string {
  return path.join(app.getPath('userData'), 'license.enc')
}

function generateDeviceId(): string {
  // Simple device fingerprint: hostname + platform + arch
  const parts = [
    require('os').hostname(),
    process.platform,
    process.arch,
  ]
  return crypto.createHash('sha256').update(parts.join('-')).digest('hex').slice(0, 16)
}

function base32Decode(encoded: string): Buffer {
  const alphabet = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ234567'
  const cleaned = encoded.toUpperCase().replace(/-/g, '').replace(/\s/g, '')
  let bits = 0
  let value = 0
  const output: number[] = []

  for (const char of cleaned) {
    const idx = alphabet.indexOf(char)
    if (idx === -1) throw new Error(`Invalid Base32 character: ${char}`)
    value = (value << 5) | idx
    bits += 5
    if (bits >= 8) {
      output.push((value >>> (bits - 8)) & 0xFF)
      bits -= 8
    }
  }
  return Buffer.from(output)
}

function verifySignature(data: Buffer, signature: Buffer): boolean {
  const verify = crypto.createVerify('SHA256')
  verify.update(data)
  return verify.verify(PUBLIC_KEY_PEM, signature)
}

function encryptLicense(payload: LicensePayload): string {
  // Simple Fernet-like encryption using AES-256-GCM with a key derived from device ID
  const deviceId = generateDeviceId()
  const key = crypto.createHash('sha256').update('mipham-quant-license-' + deviceId).digest()
  const iv = crypto.randomBytes(12)
  const cipher = crypto.createCipheriv('aes-256-gcm', key, iv)
  const json = JSON.stringify(payload)
  let encrypted = cipher.update(json, 'utf8', 'hex')
  encrypted += cipher.final('hex')
  const authTag = cipher.getAuthTag()
  // Store as: iv:authTag:ciphertext
  return `${iv.toString('hex')}:${authTag.toString('hex')}:${encrypted}`
}

function decryptLicense(encrypted: string): LicensePayload | null {
  try {
    const deviceId = generateDeviceId()
    const key = crypto.createHash('sha256').update('mipham-quant-license-' + deviceId).digest()
    const [ivHex, authTagHex, ciphertext] = encrypted.split(':')
    const iv = Buffer.from(ivHex, 'hex')
    const authTag = Buffer.from(authTagHex, 'hex')
    const decipher = crypto.createDecipheriv('aes-256-gcm', key, iv)
    decipher.setAuthTag(authTag)
    let decrypted = decipher.update(ciphertext, 'hex', 'utf8')
    decrypted += decipher.final('utf8')
    return JSON.parse(decrypted)
  } catch {
    return null
  }
}

export function activateLicense(licenseKey: string): { success: boolean; message: string } {
  try {
    // The license key format: MQ-XXXX-XXXX-XXXX-XXXX (Base32 encoded)
    if (!licenseKey.startsWith('MQ-') && !licenseKey.startsWith('MQ')) {
      return { success: false, message: 'Invalid license key format' }
    }

    const keyBody = licenseKey.replace('MQ-', 'MQ').replace(/-/g, '')
    const raw = base32Decode(keyBody)

    // First 256 bytes = RSA signature, rest = JSON payload
    const SIGNATURE_SIZE = 256 // 2048-bit RSA
    const signature = raw.subarray(0, SIGNATURE_SIZE)
    const payloadBytes = raw.subarray(SIGNATURE_SIZE)

    if (!verifySignature(payloadBytes, signature)) {
      return { success: false, message: 'License key is invalid (signature check failed)' }
    }

    const payload: LicensePayload = JSON.parse(payloadBytes.toString('utf8'))

    // Check product
    if (payload.product !== 'mipham-quant') {
      return { success: false, message: 'License key is for a different product' }
    }

    // Check expiration
    if (payload.expires_at) {
      const expires = new Date(payload.expires_at)
      if (expires < new Date()) {
        return { success: false, message: `License expired on ${payload.expires_at}` }
      }
    }

    // Check device binding (optional — only if device_id is set)
    if (payload.device_id) {
      const currentDeviceId = generateDeviceId()
      if (payload.device_id !== currentDeviceId) {
        return { success: false, message: 'License is bound to a different device' }
      }
    }

    // Save encrypted license to disk
    const encrypted = encryptLicense(payload)
    fs.writeFileSync(getLicensePath(), encrypted, 'utf8')

    return { success: true, message: 'License activated successfully' }
  } catch (err: any) {
    return { success: false, message: `Activation failed: ${err.message}` }
  }
}

export function checkLicense(): boolean {
  const licensePath = getLicensePath()
  if (!fs.existsSync(licensePath)) return false

  const encrypted = fs.readFileSync(licensePath, 'utf8')
  const payload = decryptLicense(encrypted)
  if (!payload) return false

  if (payload.expires_at) {
    return new Date(payload.expires_at) >= new Date()
  }
  return true
}

export function getLicenseInfo(): LicensePayload | null {
  const licensePath = getLicensePath()
  if (!fs.existsSync(licensePath)) return null

  const encrypted = fs.readFileSync(licensePath, 'utf8')
  return decryptLicense(encrypted)
}

export function isActivated(): boolean {
  return checkLicense()
}
