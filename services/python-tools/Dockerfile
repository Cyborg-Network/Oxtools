# Use Debian 12 (Bookworm) to maintain Python 3.12 
# while ensuring full, native Playwright OS support
FROM python:3.12-bookworm

WORKDIR /app

# 1. Install Tesseract and OpenCV system dependencies
RUN apt-get update && apt-get install -y \
    tesseract-ocr \
    tesseract-ocr-eng \
    libtesseract-dev \
    libgl1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# 2. Install base runner requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 3. Install Playwright Chromium with dependencies
# (Installed explicitly here to cache the 300MB+ browser before copying tool source code)
RUN pip install --no-cache-dir playwright==1.44.0 && playwright install --with-deps chromium

# 4. Copy all tool directories
COPY tools/ tools/

# 5. Install each tool's requirements.txt automatically
RUN for dir in tools/*/; do \
      req="${dir}requirements.txt"; \
      if [ -f "$req" ]; then \
        echo "Installing deps for $(basename $dir)..."; \
        pip install --no-cache-dir -r "$req" || true; \
      fi; \
    done



# 6. Copy the runner script
COPY runner.py .

# Set tools directory
ENV TOOLS_DIR=/app/tools

EXPOSE 9080

CMD ["uvicorn", "runner:app", "--host", "0.0.0.0", "--port", "9080"]