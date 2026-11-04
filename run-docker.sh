#!/bin/sh
set -eu

exec docker run -d --name "${CONTAINER_NAME:-quart-http3}" \
    --restart unless-stopped --pull always \
    -e HTTP3_PORT="${HTTPS_PORT:-8443}" \
    -p "${HTTP_PORT:-8080}:80/tcp" \
    -p "${HTTPS_PORT:-8443}:443/tcp" \
    -p "${HTTPS_PORT:-8443}:443/udp" \
    "${IMAGE:-justdanz/quart-http3:latest}"
