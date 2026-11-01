#!/bin/bash
set -Eeuo pipefail

# Fixed internal ports keep the Unraid template and healthcheck consistent.
export DATA_DIR=/data PORT=3000 NGINX_PORT=8080 BACKEND=127.0.0.1
export TRUST_PROXY=1 RESOLVER=127.0.0.11
export BASE_PATH="${BASE_PATH:-}" CF_CONNECTING_IP="${CF_CONNECTING_IP:-}"
export MEDIA_UPLOAD_MAX="${MEDIA_UPLOAD_MAX:-48m}"
export CONTENT_SECURITY_POLICY="${CONTENT_SECURITY_POLICY:-$(cat /etc/opengym/content-security-policy)}"

/bin/sh /etc/opengym/check-base-path.sh
mkdir -p /data /run/nginx
# Whitelist substitutions: nginx's own $host, $uri, etc. must survive rendering.
envsubst '${NGINX_PORT} ${BACKEND} ${PORT} ${RESOLVER} ${BASE_PATH} ${CF_CONNECTING_IP} ${MEDIA_UPLOAD_MAX} ${CONTENT_SECURITY_POLICY}' \
    < /etc/opengym/default.conf.template > /etc/nginx/http.d/default.conf
nginx -t

api_pid=''
web_pid=''
stop_services() {
    trap '' TERM INT
    # QUIT lets nginx finish in-flight requests; TERM stops Node as upstream does.
    if [[ -n "$web_pid" ]]; then kill -QUIT "$web_pid" 2>/dev/null || true; fi
    if [[ -n "$api_pid" ]]; then kill -TERM "$api_pid" 2>/dev/null || true; fi
    # Bound graceful shutdown so Docker's stop deadline is not exceeded.
    (
        sleep 5
        if [[ -n "$web_pid" ]]; then kill -KILL "$web_pid" 2>/dev/null || true; fi
        if [[ -n "$api_pid" ]]; then kill -KILL "$api_pid" 2>/dev/null || true; fi
    ) &
    local timeout_pid=$!
    if [[ -n "$api_pid" ]]; then wait "$api_pid" 2>/dev/null || true; fi
    if [[ -n "$web_pid" ]]; then wait "$web_pid" 2>/dev/null || true; fi
    kill "$timeout_pid" 2>/dev/null || true
    wait "$timeout_pid" 2>/dev/null || true
}
trap 'stop_services; exit 0' TERM INT

cd /app
node server.js &
api_pid=$!
nginx -g 'daemon off;' &
web_pid=$!

# A failed service must fail the container so Unraid's restart policy can recover it.
status=0
wait -n "$api_pid" "$web_pid" || status=$?
echo "openGym: a service exited (status $status); stopping the container" >&2
stop_services
(( status != 0 )) || status=1
exit "$status"
