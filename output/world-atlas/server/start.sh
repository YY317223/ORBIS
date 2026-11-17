#!/usr/bin/env sh
# ORBIS · 本地数据服务（macOS / Linux）
# 用法：./start.sh   或   ./start.sh --port 9000
cd "$(dirname "$0")" || exit 1
exec python3 app.py --open "$@"
