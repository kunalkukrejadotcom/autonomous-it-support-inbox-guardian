# Use official Python runtime as a parent image
FROM python:3.11-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PORT=8080

# Set working directory
WORKDIR /app

# Copy dependency files and install packages
COPY pyproject.toml README.md ./
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir .

# Copy agent code and configuration prompts
COPY agent/ ./agent/

# Expose port (Cloud Run sets PORT env variable, defaulting to 8080)
EXPOSE 8080

# Command to run the application using uvicorn
CMD ["sh", "-c", "uvicorn agent.main:app --host 0.0.0.0 --port ${PORT}"]
