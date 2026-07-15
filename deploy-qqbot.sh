#!/bin/bash
# ================================================================
# Mipham Quant — 一键部署到 QQbot 轻量服务器
# ================================================================
# 用法: ./deploy-qqbot.sh
#
# 前置条件:
#   1. 本地有 SSH 私钥 ~/.ssh/id_ed25519
#   2. QQbot 服务器上已添加对应公钥到 ~/.ssh/authorized_keys
#   3. 服务器上已安装 Docker + Docker Compose
# ================================================================
set -e

SERVER="ubuntu@192.144.235.27"
REMOTE_DIR="/opt/mipham-quant"
SSH_KEY="$HOME/.ssh/id_ed25519"
SSH_OPTS="-i $SSH_KEY -o StrictHostKeyChecking=accept-new"

echo "========================================="
echo "  Mipham Quant — QQbot 一键部署"
echo "  $(date '+%Y-%m-%d %H:%M:%S')"
echo "========================================="

# ── 1. 同步代码 ──
echo ""
echo "[1/4] Rsync 代码 → QQbot..."
rsync -avz --delete -e "ssh $SSH_OPTS" \
  --exclude '.git' \
  --exclude 'node_modules' \
  --exclude 'apps/frontend/node_modules' \
  --exclude 'backend_api_python/.env' \
  --exclude 'backend_api_python/.venv' \
  --exclude 'frontend/dist/maps' \
  --exclude '__pycache__' \
  --exclude '*.pyc' \
  --exclude '.pytest_cache' \
  --exclude '*.egg-info' \
  ./ \
  "$SERVER:$REMOTE_DIR"
echo "  ✅ 代码同步完成"

# ── 2. 修复权限 + 配置 ──
echo ""
echo "[2/4] 配置环境..."
ssh $SSH_OPTS "$SERVER" bash -s << 'ENDSSH'
set -e
cd /opt/mipham-quant

# Fix permissions
sudo chown -R ubuntu:ubuntu /opt/mipham-quant 2>/dev/null || true

# Generate .env if missing
if [ ! -f backend_api_python/.env ]; then
  cp backend_api_python/env.example backend_api_python/.env
  NEW_KEY=$(python3 -c "import secrets; print(secrets.token_hex(32))")
  sed -i "s/SECRET_KEY=.*/SECRET_KEY=${NEW_KEY}/" backend_api_python/.env
  NEW_PWD=$(python3 -c "import secrets; print(secrets.token_urlsafe(16))")
  sed -i "s/ADMIN_PASSWORD=.*/ADMIN_PASSWORD=${NEW_PWD}/" backend_api_python/.env
  echo "  ✅ .env 已生成 (含随机 SECRET_KEY + ADMIN_PASSWORD)"
else
  echo "  ✅ .env 已存在"
fi
ENDSSH

# ── 3. 构建并重启 ──
echo ""
echo "[3/4] Docker Compose 构建 + 启动 (可能需要 5-10 分钟)..."
ssh $SSH_OPTS "$SERVER" bash -s << 'ENDSSH'
set -e
cd /opt/mipham-quant
docker compose -f docker-compose.yml -f docker-compose.prod.yml down --remove-orphans 2>/dev/null || true
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build
ENDSSH
echo "  ✅ 容器已启动"

# ── 4. 健康检查 ──
echo ""
echo "[4/4] 等待服务就绪..."
for i in $(seq 1 30); do
  if ssh $SSH_OPTS "$SERVER" "curl -sf http://localhost:5010/api/health" > /dev/null 2>&1; then
    echo "  ✅ 后端就绪 (${i}x2 秒)"
    break
  fi
  sleep 2
done

# ── 验证 ──
echo ""
echo "========================================="
echo "  部署完成"
echo "  🌐 https://quant.onemipham.com"
echo "  ❤️  http://192.144.235.27:5010/api/health"
echo ""
HTTP_CODE=$(ssh $SSH_OPTS "$SERVER" "curl -s -o /dev/null -w '%{http_code}' http://localhost:5010/api/health")
echo "  后端状态: HTTP $HTTP_CODE"
if [ "$HTTP_CODE" = "200" ]; then
  echo "  ✅ 部署成功"
else
  echo "  ⚠️ 后端未就绪，检查日志: ssh $SERVER 'docker compose logs backend'"
fi
echo "========================================="
