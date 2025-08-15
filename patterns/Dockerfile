FROM python:3.11-slim

WORKDIR /app

# Copy requirements and install dependencies
COPY requirements.txt .
COPY requirements-test.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install --no-cache-dir -r requirements-test.txt

# Create necessary directories
RUN mkdir -p /app/miando/logs

# Create the log file
RUN touch /app/miando/logs/json_exporter.log

# Copy patterns source code
COPY . ./patterns/

# Copy SSL certificates
COPY server.crt server.key ./patterns/

# Set working directory to patterns for running scripts
WORKDIR /app/patterns/json_split

# Set Python path to include both patterns and test directories (tests will be mounted)
ENV PYTHONPATH=/app:/app/patterns:/app/patterns/json_split:/app/tests
ENV DB_HOST=miando-db
ENV DB_PORT=5432
ENV DB_NAME=miando
ENV DB_USER=miando
ENV DB_PASSWORD=changeme
ENV SYMBOL=XAUUSD

# Make scripts executable
RUN chmod +x *.py

# Default command - can be overridden
CMD ["python3", "main_live.py", "--continuous"]
