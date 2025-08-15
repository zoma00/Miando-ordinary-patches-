FROM postgres:16

# Enable SSL
RUN mkdir -p /var/lib/postgresql/certs
COPY server.crt /var/lib/postgresql/certs/server.crt
COPY server.key /var/lib/postgresql/certs/server.key
RUN chown postgres:postgres /var/lib/postgresql/certs/server.* && \
    chmod 600 /var/lib/postgresql/certs/server.key

ENV POSTGRES_DB=miando
ENV POSTGRES_USER=miando
ENV POSTGRES_PASSWORD=changeme

# Add schema
COPY schema.sql /docker-entrypoint-initdb.d/schema.sql

# Add script to enable SSL
COPY enable_ssl.sh /docker-entrypoint-initdb.d/zz_enable_ssl.sh
RUN chmod +x /docker-entrypoint-initdb.d/zz_enable_ssl.sh

# Add startup script that fixes permissions
COPY fix_permissions.sh /usr/local/bin/
RUN chmod +x /usr/local/bin/fix_permissions.sh

ENTRYPOINT ["/usr/local/bin/fix_permissions.sh"]
