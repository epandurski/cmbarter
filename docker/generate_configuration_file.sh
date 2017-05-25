#!/bin/bash
#
# This file is used by "Dockerfile.proxy".

set -e
envsubst '$PROXY_PASS_TO:$CMBARTER_HOST' < /etc/nginx/nginx.template > /etc/nginx/nginx.conf
exec "$@"
