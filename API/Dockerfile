FROM python:3.12-slim

WORKDIR /app

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Expose port 8080
ENV PORT 8080

# Run the application
CMD exec uvicorn main:app --host 0.0.0.0 --port 8080
