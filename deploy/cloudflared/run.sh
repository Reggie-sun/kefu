#!/bin/sh
set -euo pipefail

: "${CLOUDFLARED_TUNNEL_ID:?Set CLOUDFLARED_TUNNEL_ID in .env.deploy}"
: "${WX_DOMAIN:?Set WX_DOMAIN in .env.deploy}"
UPSTREAM_URL="${CLOUDFLARED_UPSTREAM_URL:-https://caddy:443}"
PROTOCOL="${CLOUDFLARED_PROTOCOL:-quic}"
CONFIG_OVERRIDE="/etc/cloudflared/config.yml"
CONFIG_PATH="/tmp/cloudflared-config.yml"
CREDENTIALS_FILE="/etc/cloudflared/credentials/${CLOUDFLARED_TUNNEL_ID}.json"

if [ ! -f "$CREDENTIALS_FILE" ]; then
    echo "Missing Cloudflared credentials JSON at $CREDENTIALS_FILE" >&2
    exit 1
fi

if [ -f "$CONFIG_OVERRIDE" ]; then
    echo "Detected /etc/cloudflared/config.yml, rendering with env and using it"
    envsubst < "$CONFIG_OVERRIDE" > "$CONFIG_PATH"
    exec cloudflared tunnel --config "$CONFIG_PATH" --no-autoupdate run
fi

cat >"$CONFIG_PATH" <<EOF_CFG
tunnel: ${CLOUDFLARED_TUNNEL_ID}
credentials-file: ${CREDENTIALS_FILE}
protocol: ${PROTOCOL}

ingress:
  - hostname: ${WX_DOMAIN}
    service: ${UPSTREAM_URL}
    originRequest:
      originServerName: ${WX_DOMAIN}
      httpHostHeader: ${WX_DOMAIN}
      http2Origin: true
      connectTimeout: 30s
      tlsTimeout: 10s
EOF_CFG

if [ -n "${GATEWAY_DOMAIN:-}" ]; then
cat >>"$CONFIG_PATH" <<EOF_CFG
  - hostname: ${GATEWAY_DOMAIN}
    service: ${UPSTREAM_URL}
    originRequest:
      originServerName: ${GATEWAY_DOMAIN}
      httpHostHeader: ${GATEWAY_DOMAIN}
      http2Origin: true
      connectTimeout: 30s
      tlsTimeout: 10s
EOF_CFG
fi

if [ -n "${DASH_DOMAIN:-}" ]; then
cat >>"$CONFIG_PATH" <<EOF_CFG
  - hostname: ${DASH_DOMAIN}
    service: ${UPSTREAM_URL}
    originRequest:
      originServerName: ${DASH_DOMAIN}
      httpHostHeader: ${DASH_DOMAIN}
      http2Origin: true
      connectTimeout: 30s
      tlsTimeout: 10s
EOF_CFG
fi

cat >>"$CONFIG_PATH" <<'EOF_CFG'
  - service: http_status:404
EOF_CFG

exec cloudflared tunnel --config "$CONFIG_PATH" --no-autoupdate run
