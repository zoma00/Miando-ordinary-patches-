#!/bin/bash
# Generate self-signed SSL certificate for PostgreSQL
openssl req -new -x509 -days 365 -nodes \
  -out server.crt \
  -keyout server.key \
  -subj "/C=DE/ST=Berlin/L=Berlin/O=Miando/OU=IT/CN=localhost"
chmod 600 server.key
