# Use a minimal Python image
FROM python:3.12-slim

WORKDIR /app

# Copy requirements if needed
COPY requirements.txt . 
RUN pip install -r requirements.txt

# Create log directory
RUN mkdir -p /app/logs

# Copy all code
COPY . .

# Run with Honcho
RUN pip install honcho

CMD ["honcho", "start"]
