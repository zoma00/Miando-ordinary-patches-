FROM python:3.11-slim

WORKDIR /app

# Copy requirements first for better Docker layer caching
COPY requirements.txt .

# Install required Python packages
RUN pip install --no-cache-dir -r requirements.txt

# Copy your optimized bot script and SSL certificate
COPY indikator_bot_clean.py .
COPY indikator_bot_turbo_fixed.py .
COPY server.crt .

CMD ["python3", "indikator_bot_clean.py"]
