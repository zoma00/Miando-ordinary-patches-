#!/bin/bash
set -e

# Fix permissions on SSL key files
chown postgres:postgres /var/lib/postgresql/certs/server.key
chmod 600 /var/lib/postgresql/certs/server.key

# Then start PostgreSQL
exec docker-entrypoint.sh postgres
