#!/usr/bin/env bash
# Compound Ops - LAN server launcher (Linux/macOS)
cd "$(dirname "$0")"
PORT="${1:-8080}"
echo "============================================"
echo "  COMPOUND OPS - LAN SERVER (port $PORT)"
echo "============================================"
# try to open the firewall (needs sudo; skip silently if not available)
if command -v ufw >/dev/null 2>&1; then sudo -n ufw allow "$PORT/tcp" 2>/dev/null && echo "Firewall: opened $PORT/tcp" || echo "Firewall: run 'sudo ufw allow $PORT/tcp' if other PCs cannot connect"
elif command -v firewall-cmd >/dev/null 2>&1; then sudo -n firewall-cmd --add-port="$PORT/tcp" 2>/dev/null && echo "Firewall: opened $PORT/tcp" || echo "Firewall: run 'sudo firewall-cmd --add-port=$PORT/tcp' if other PCs cannot connect"
fi
node lan_server.js "$PORT"
