#!/bin/bash
#
# This file is used by "Dockerfile.web".

if [[ -z $CMBARTER_SECRET_KEY ]]; then
    if [[ -s /run/secrets/CMBARTER_SECRET_KEY ]]; then
	export CMBARTER_SECRET_KEY=$(cat /run/secrets/CMBARTER_SECRET_KEY)
    else
	echo 'CMBARTER_SECRET_KEY is not set, /run/secrets/CMBARTER_SECRET_KEY is not present.'
	exit 1;
    fi
fi

if [[ -z $CMBARTER_REGISTRATION_SECRET ]]; then
    if [[ -s /run/secrets/CMBARTER_REGISTRATION_SECRET ]]; then
	export CMBARTER_REGISTRATION_SECRET=$(cat /run/secrets/CMBARTER_REGISTRATION_SECRET)
    fi
fi

mkdir -p /var/log/postgresql
chmod -R 755 /var/log/postgresql
chown -R postgres:postgres /var/log/postgresql

mkdir -p /etc/pgbouncer
touch /etc/pgbouncer/userlist.txt
cat > /etc/pgbouncer/pgbouncer.ini <<EOF
[databases]
cmbarter = ${CMBARTER_DSN}

[pgbouncer]
listen_addr = 127.0.0.1
listen_port = 5432
logfile = /var/log/postgresql/pgbouncer.log
pidfile = /var/run/postgresql/pgbouncer.pid
unix_socket_dir = /var/run/postgresql
auth_type = any
auth_file = /etc/pgbouncer/userlist.txt
pool_mode = session
server_reset_query = DISCARD ALL
max_client_conn = 100
default_pool_size = 20
dns_max_ttl = 1
EOF

rm -f /var/run/postgresql/pgbouncer.pid
pgbouncer -q -u postgres /etc/pgbouncer/pgbouncer.ini &

export CMBARTER_DSN="dbname=cmbarter"

exec "$@"
