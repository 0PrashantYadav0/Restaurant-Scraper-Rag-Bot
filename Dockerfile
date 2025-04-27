FROM python:3.10-slim

# Set working directory
WORKDIR /app

# Install Node.js for frontend build
RUN apt-get update && \
    apt-get install -y curl && \
    curl -fsSL https://deb.nodesource.com/setup_18.x | bash - && \
    apt-get install -y nodejs && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy frontend files and build
COPY frontend/ ./frontend/
RUN cd frontend && \
    npm install && \
    npm run build

# Copy the rest of the application
COPY . .

# Create necessary directories if they don't exist
RUN mkdir -p data/raw data/processed logs

# Expose port for the API
EXPOSE 8000

# Command to run the application
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]