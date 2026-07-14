#!/bin/bash
# ================================================================
# Mipham Quant 线上版 — 腾讯云生产部署
# ================================================================
# 服务器: 192.144.235.27 (2C/2GB/40GB 腾讯云 CVM)
# 子域名: quant.onemipham.com
# ================================================================
set -e

SERVER="root@192.144.235.27"
REMOTE_DIR="/opt/mipham-quant"

echo "========================================="
echo "  Mipham Quant 线上版 部署"
echo "  $(date '+%Y-%m-%d %H:%M')"
echo "========================================="

# ── 1. 同步代码 ──
echo ""
echo "[1/5] Rsync → 腾讯云..."
rsync -avz --delete \
  --exclude 'node_modules' \
  --exclude 'apps/frontend/node_modules' \
  --exclude '.git' \
  --exclude 'backend_api_python/.env' \
  --exclude 'backend_api_python/.venv' \
  --exclude 'frontend/dist/maps' \
  --exclude '.playwright-mcp' \
  --exclude '__pycache__' \
  --exclude '*.pyc' \
  --exclude '*.egg-info' \
  --exclude '.pytest_cache' \
  ./ \
  "$SERVER:$REMOTE_DIR"
echo "  ✅ 代码同步完成"

# ── 2. 配置环境 ──
echo ""
echo "[2/5] 配置生产环境..."
ssh "$SERVER" bash -s << 'ENDSSH'
set -e
cd /opt/mipham-quant

# 首次部署：生成 .env
if [ ! -f backend_api_python/.env ]; then
  cp backend_api_python/env.example backend_api_python/.env
  NEW_KEY=$(python3 -c "import secrets; print(secrets.token_hex(32))")
  sed -i "s/SECRET_KEY=.*/SECRET_KEY=${NEW_KEY}/" backend_api_python/.env
  sed -i "s/ADMIN_USER=.*/ADMIN_USER=mipham/" backend_api_python/.env
  sed -i "s/ADMIN_PASSWORD=.*/ADMIN_PASSWORD=mipham2026/" backend_api_python/.env
  sed -i "s/DEBUG=.*/DEBUG=false/" backend_api_python/.env
  echo "  ✅ .env 已生成 (生产模式)"
else
  echo "  ✅ .env 已存在"
fi

# 确保生产配置
sed -i 's/^PYTHON_API_DEBUG=.*/PYTHON_API_DEBUG=false/' backend_api_python/.env 2>/dev/null || true
sed -i 's/^ENABLE_REGISTRATION=.*/ENABLE_REGISTRATION=true/' backend_api_python/.env 2>/dev/null || true
ENDSSH

# ── 3. 构建前端 ──
echo ""
echo "[3/5] 构建前端..."
ssh "$SERVER" bash -s << 'ENDSSH'
set -e
cd /opt/mipham-quant/apps/frontend
if command -v pnpm &> /dev/null; then
  pnpm install --frozen-lockfile 2>/dev/null || pnpm install
  pnpm build
  echo "  ✅ 前端构建完成"
else
  echo "  ⚠️ pnpm 未安装，跳过前端构建（使用已有 dist）"
fi
ENDSSH

# ── 4. 重启服务 ──
echo ""
echo "[4/5] 重启 Docker 服务..."
ssh "$SERVER" << 'ENDSSH'
set -e
cd /opt/mipham-quant
docker compose down --remove-orphans
docker compose up -d --build

# 等待健康检查
echo "  等待服务就绪..."
for i in $(seq 1 30); do
  if curl -sf http://127.0.0.1:5010/api/health > /dev/null 2>&1; then
    echo "  ✅ 后端就绪"
    break
  fi
  sleep 2
done
ENDSSH

# ── 5. Nginx 重载 ──
echo ""
echo "[5/5] 配置 Nginx..."
ssh "$SERVER" bash -s << 'ENDSSH'
set -e
if [ -f /opt/mipham-quant/infrastructure/nginx/quant.onemipham.com.conf ]; then
  # 宝塔面板 Nginx 路径
  BT_NGINX="/www/server/panel/vhost/nginx"
  if [ -d "$BT_NGINX" ]; then
    cp /opt/mipham-quant/infrastructure/nginx/quant.onemipham.com.conf "$BT_NGINX/quant.onemipham.com.conf"
    nginx -s reload 2>/dev/null || /www/server/nginx/sbin/nginx -s reload 2>/dev/null || true
    echo "  ✅ Nginx 配置已更新并重载"
  else
    echo "  ⚠️ 非宝塔环境，跳过 Nginx 配置"
  fi
fi
ENDSSH

# ── 验证 ──
echo ""
echo "========================================="
echo "  部署完成"
echo "  🌐 https://quant.onemipham.com"
echo "  ❤️  http://192.144.235.27:5010/api/health"
echo ""
echo "  登录: mipham / mipham2026"
echo "========================================="

# 快速验证
sleep 3
HTTP_CODE=$(curl -s -o /dev/null -w '%{http_code}' http://192.144.235.27:5010/api/health)
echo "  后端状态: HTTP $HTTP_CODE"
if [ "$HTTP_CODE" = "200" ]; then
  echo "  ✅ 部署成功"
else
  echo "  ⚠️ 后端未就绪，请检查日志: ssh $SERVER 'docker compose logs backend'"
fi
