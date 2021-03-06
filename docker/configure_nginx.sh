#!/bin/bash
#
# This file is used by "Dockerfile.proxy".

set -e
envsubst '$PROXY_PASS_TO:$CMBARTER_HOST' < /etc/nginx/nginx.template > /etc/nginx/nginx.conf
if [[ -e /run/secrets/cert.pem ]] && [[ -e /run/secrets/key.pem ]]; then
   cp /run/secrets/cert.pem /run/secrets/key.pem /etc/nginx/ssl/
fi

iptables -P INPUT DROP
iptables -A INPUT -m state --state RELATED,ESTABLISHED -j ACCEPT
iptables -A INPUT -m state --state NEW -m limit --limit 5000/second --limit-burst 250 -j ACCEPT

exec "$@"
