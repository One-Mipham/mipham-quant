#!/bin/bash
DIR="$(cd "$(dirname "$0")" && pwd)"
export DB_TYPE=sqlite
export DB_PATH="${DB_PATH:-$HOME/.mipham-quant/quant.db}"
export SINGLE_USER_MODE=true
export HOST=127.0.0.1
export PORT="${PORT:-5000}"
mkdir -p "$(dirname "$DB_PATH")"
exec python3 "$DIR/run.py"
