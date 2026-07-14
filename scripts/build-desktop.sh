#!/bin/bash
# Mipham Quant Desktop — Full Build Script
set -e

echo "=== Building Mipham Quant Desktop v1.0.0 ==="

# Step 1: Build Python backend (on macOS only; Windows needs separate build)
if [[ "$OSTYPE" == "darwin"* ]]; then
    echo ""
    echo "[1/4] Building Python backend..."
    cd backend_api_python
    python3 build.py
    cd ..
    echo "Backend built: backend_api_python/dist/"
    ls -lh backend_api_python/dist/
else
    echo "[1/4] Skipping Python build (not macOS — build on target platform)"
    mkdir -p backend_api_python/dist
    touch backend_api_python/dist/mipham-quant-backend
fi

# Step 2: Build frontend
echo ""
echo "[2/4] Building frontend..."
cd apps/frontend
pnpm install --frozen-lockfile
pnpm build
cd ../..
echo "Frontend built: frontend/dist/"

# Step 3: Compile Electron TypeScript
echo ""
echo "[3/4] Compiling Electron..."
pnpm tsc -p electron/tsconfig.json
echo "Electron compiled: dist-electron/"

# Step 4: Package with electron-builder
echo ""
echo "[4/4] Packaging with electron-builder..."
if [[ "$OSTYPE" == "darwin"* ]]; then
    pnpm electron:build:mac
    echo ""
    echo "=== Build Complete ==="
    ls -lh dist/*.dmg dist/*.zip 2>/dev/null || echo "Check dist/ for output"
else
    pnpm electron:build:win
    echo ""
    echo "=== Build Complete ==="
    ls -lh dist/*.exe 2>/dev/null || echo "Check dist/ for output"
fi
