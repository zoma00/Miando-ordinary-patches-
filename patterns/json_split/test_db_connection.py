#!/usr/bin/env python3
# Test database connection from patterns container

from common import get_cursor

print('Testing database connection...')
try:
    with get_cursor(dict_cursor=True) as cur:
        cur.execute('SELECT version()')
        version = cur.fetchone()
        print('✅ Database connection successful!')
        if version:
            print(f'PostgreSQL version: {version["version"][:50]}...')
        else:
            print('PostgreSQL version: Unknown')
except Exception as e:
    print(f'❌ Database connection failed: {e}')
