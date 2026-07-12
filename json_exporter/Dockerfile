FROM python:3.9-slim

WORKDIR /app

# Copy requirements and install dependencies
COPY requirements.txt* ./
RUN pip install --no-cache-dir psycopg2-binary python-dateutil

# Copy application files
COPY . .

# Run the json exporter
CMD ["python", "json_exporter.py"]
