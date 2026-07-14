#!/bin/bash
cd "$(dirname "$0")"
echo "🛑 Stopping Mipham Quant..."
docker-compose down
echo "✅ Stopped"
