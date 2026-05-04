FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    chromium \
    tesseract-ocr \
    libtesseract-dev \
    libgl1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Install base runner requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy all tool directories
COPY tools/ tools/

# Install each tool's requirements.txt automatically
RUN for dir in tools/*/; do \
      req="${dir}requirements.txt"; \
      if [ -f "$req" ]; then \
        echo "Installing deps for $(basename $dir)..."; \
        pip install --no-cache-dir -r "$req" || true; \
      fi; \
    done

# Install Playwright Chromium binary WITHOUT the failing deps flag
RUN playwright install chromium

# Copy the runner
COPY runner.py .

# Set tools directory
ENV TOOLS_DIR=/app/tools

EXPOSE 9080

CMD ["uvicorn", "runner:app", "--host", "0.0.0.0", "--port", "9080"]