#!/bin/bash
set -e

echo "🚀 Mipham Quant — Starting..."

cd "$(dirname "$0")"

# Check Docker
if ! command -v docker &> /dev/null; then
    echo "❌ Please install Docker Desktop first: https://www.docker.com/products/docker-desktop/"
    exit 1
fi

# Check .env
if [ ! -f backend_api_python/.env ]; then
    echo "📝 First run: generating config..."
    cp backend_api_python/env.example backend_api_python/.env
    NEW_KEY=$(python3 -c "import secrets; print(secrets.token_hex(32))")
    sed -i '' "s/SECRET_KEY=.*/SECRET_KEY=${NEW_KEY}/" backend_api_python/.env
    sed -i '' "s/ADMIN_USER=.*/ADMIN_USER=mipham/" backend_api_python/.env
    sed -i '' "s/ADMIN_PASSWORD=.*/ADMIN_PASSWORD=mipham2026/" backend_api_python/.env
    echo "✅ Config generated, SECRET_KEY auto-set"
fi

# Ensure default SECRET_KEY is replaced
if grep -q "SECRET_KEY=mipham-quant-secret-key-change-me" backend_api_python/.env; then
    echo "⚠️  Default SECRET_KEY detected, replacing..."
    NEW_KEY=$(python3 -c "import secrets; print(secrets.token_hex(32))")
    sed -i '' "s/SECRET_KEY=.*/SECRET_KEY=${NEW_KEY}/" backend_api_python/.env
fi

# Start services
echo "🐳 Starting Docker services..."
docker-compose up -d --build

# Wait for backend health
echo "⏳ Waiting for services..."
for i in {1..30}; do
    if curl -sf http://localhost:5010/api/health > /dev/null 2>&1; then
        echo "✅ Backend ready"
        break
    fi
    sleep 2
done

# Open browser
echo "🌐 Opening browser..."
sleep 2
open http://localhost:8888

echo ""
echo "════════════════════════════════════════"
echo "  Mipham Quant v0.1.0"
echo "  Frontend: http://localhost:8888"
echo "  Backend:  http://localhost:5010/api/health"
echo "  Login:    mipham / mipham2026"
echo "════════════════════════════════════════"
echo ""
echo "Stop: ./stop.sh"
