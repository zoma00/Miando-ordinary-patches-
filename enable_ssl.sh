#!/bin/bash
set -e

# Set SSL options in postgresql.conf
cat <<EOF >> /var/lib/postgresql/data/postgresql.conf
ssl = on
ssl_cert_file = '/var/lib/postgresql/certs/server.crt'
ssl_key_file = '/var/lib/postgresql/certs/server.key'
EOF

echo "SSL configuration added to postgresql.conf"
