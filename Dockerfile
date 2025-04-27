FROM python:3-alpine

# Set working directory
WORKDIR /app

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install -r requirements.txt

# Copy the rest of the application
COPY . .

# Create necessary directories if they don't exist
RUN mkdir -p data/raw data/processed logs

# Expose port for the API
EXPOSE 8000

# Command to run the application
CMD [ "python3", "main.py", "--backend" ]