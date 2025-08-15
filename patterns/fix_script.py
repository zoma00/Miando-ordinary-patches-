#!/usr/bin/env python3
import os
import sys

# Define the variables that need to be added
variables_to_add = """
# Get database connection parameters from environment variables
import os
DB_HOST = os.getenv('DB_HOST', 'miando-db')
DB_PORT = os.getenv('DB_PORT', '5432')
DB_NAME = os.getenv('DB_NAME', 'miando')
DB_USER = os.getenv('DB_USER', 'miando')
DB_PASSWORD = os.getenv('DB_PASSWORD', 'changeme')
"""

# Read the current file
with open('/app/json_exporter.py', 'r') as f:
    content = f.read()

# Find the position where we want to insert the variables
target_line = 'DB_CONFIG = {'
position = content.find(target_line)

if position > 0:
    # Insert the variables before DB_CONFIG = {
    new_content = content[:position] + variables_to_add + content[position:]
    
    # Write the modified content back to the file
    with open('/app/json_exporter.py', 'w') as f:
        f.write(new_content)
    
    print("Successfully updated the script!")
else:
    print("Could not find the target line in the script.")
    sys.exit(1)
