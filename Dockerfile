FROM python:3.12-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Playwright browsers
RUN pip install playwright
RUN playwright install chromium
RUN playwright install-deps chromium

# Copy project files
COPY pyproject.toml ./
COPY src/ ./src/

# Install Python dependencies
RUN pip install -e .

# Expose port
EXPOSE 8000

# Run the application
CMD ["python", "-m", "pricerecon"]