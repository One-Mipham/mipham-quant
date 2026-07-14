#!/usr/bin/env python3
"""
Mipham Quant — License Key Generator
=====================================
Generates RSA-signed license keys for desktop edition.

⚠️  KEEP THE PRIVATE KEY SECRET. Never commit it or ship it.
    Store it offline. Only the PUBLIC KEY goes into the app.

Usage:
    python scripts/generate-license.py --email buyer@example.com

Output:
    MQ-XXXX-XXXX-XXXX-XXXX (5 blocks, Base32 encoded)
"""

import argparse
import base64
import json
import os
import sys
from datetime import datetime, timedelta
from typing import Optional

# ---- RSA Key Generation (run once) ----
# If you haven't generated keys yet, uncomment and run:
#
#   from cryptography.hazmat.primitives.asymmetric import rsa
#   from cryptography.hazmat.primitives import serialization
#   private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
#   public_key = private_key.public_key()
#   with open('license_private.pem', 'wb') as f:
#       f.write(private_key.private_bytes(
#           encoding=serialization.Encoding.PEM,
#           format=serialization.PrivateFormat.PKCS8,
#           encryption_algorithm=serialization.NoEncryption()))
#   with open('license_public.pem', 'wb') as f:
#       f.write(public_key.public_bytes(
#           encoding=serialization.Encoding.PEM,
#           format=serialization.PublicFormat.SubjectPublicKeyInfo))

# ---- Configuration ----
PRODUCT = "mipham-quant"
DEFAULT_EXPIRY_DAYS = 36500  # ~100 years = effectively permanent

# Path to private key (absolute or relative to this script)
PRIVATE_KEY_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "..", "license_private.pem"
)

try:
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import padding, rsa
    HAS_CRYPTO = True
except ImportError:
    HAS_CRYPTO = False
    print("⚠️  'cryptography' not installed. Run: pip install cryptography")
    print("   Then re-run this script.")
    sys.exit(1)

BASE32_ALPHABET = "ABCDEFGHIJKLMNOPQRSTUVWXYZ234567"


def base32_encode(data: bytes) -> str:
    """Encode bytes to Base32 string (RFC 4648, uppercase, no padding)."""
    result = []
    bits = 0
    value = 0
    for byte in data:
        value = (value << 8) | byte
        bits += 8
        while bits >= 5:
            result.append(BASE32_ALPHABET[(value >> (bits - 5)) & 0x1F])
            bits -= 5
    if bits > 0:
        result.append(BASE32_ALPHABET[(value << (5 - bits)) & 0x1F])
    return "".join(result)


def format_license_key(encoded: str) -> str:
    """Format as MQ-XXXX-XXXX-XXXX-XXXX (5 blocks of 4)."""
    # Strip MQ prefix if present, then chunk into blocks of 4
    raw = encoded.upper()
    if raw.startswith("MQ"):
        raw = raw[2:]
    blocks = [raw[i:i+4] for i in range(0, len(raw), 4)]
    return "MQ-" + "-".join(blocks[:5])


def sign_payload(payload: dict, private_key_path: str) -> bytes:
    """Sign JSON payload with RSA-SHA256."""
    with open(private_key_path, "rb") as f:
        private_key = serialization.load_pem_private_key(f.read(), password=None)

    payload_json = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    signature = private_key.sign(
        payload_json,
        padding.PKCS1v15(),
        hashes.SHA256(),
    )
    # Concatenate: signature + payload
    return signature + payload_json


def generate_license(
    email: str,
    device_id: Optional[str] = None,
    expiry_days: int = DEFAULT_EXPIRY_DAYS,
    features: Optional[list] = None,
) -> str:
    """Generate a license key for the given email."""
    if not os.path.exists(PRIVATE_KEY_PATH):
        print(f"❌ Private key not found at: {PRIVATE_KEY_PATH}")
        print("   Generate keys first (see script header).")
        sys.exit(1)

    if features is None:
        features = ["all"]

    issued_at = datetime.utcnow().strftime("%Y-%m-%d")
    expires_at = (datetime.utcnow() + timedelta(days=expiry_days)).strftime("%Y-%m-%d")

    payload = {
        "product": PRODUCT,
        "email": email,
        "issued_at": issued_at,
        "expires_at": expires_at,
        "features": features,
    }

    if device_id:
        payload["device_id"] = device_id

    signed = sign_payload(payload, PRIVATE_KEY_PATH)
    encoded = base32_encode(signed)
    return format_license_key(encoded)


def main():
    parser = argparse.ArgumentParser(description="Mipham Quant License Generator")
    parser.add_argument("--email", required=True, help="Buyer email address")
    parser.add_argument("--device-id", help="Bind to specific device ID")
    parser.add_argument("--expiry-days", type=int, default=DEFAULT_EXPIRY_DAYS,
                        help=f"Days until expiry (default: {DEFAULT_EXPIRY_DAYS})")
    parser.add_argument("--features", nargs="+", default=["all"],
                        help="Enabled features (default: all)")

    args = parser.parse_args()

    license_key = generate_license(
        email=args.email,
        device_id=args.device_id,
        expiry_days=args.expiry_days,
        features=args.features,
    )

    print()
    print("=" * 50)
    print("  Mipham Quant License Key")
    print("=" * 50)
    print(f"  {license_key}")
    print("=" * 50)
    print(f"  Email:     {args.email}")
    print(f"  Device:    {args.device_id or 'any'}")
    print(f"  Expires:   {args.expiry_days} days from now")
    print(f"  Features:  {', '.join(args.features)}")
    print("=" * 50)
    print()
    print("Send this key to the buyer. They enter it in:")
    print("  Mipham Quant → Help → Enter License Key")
    print()


if __name__ == "__main__":
    main()
