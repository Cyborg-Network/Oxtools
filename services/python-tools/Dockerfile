FROM python:3.12-slim

WORKDIR /app

# Install base runner requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy all tool directories
COPY tools/ tools/

# Install each tool's requirements.txt automatically
# Scans tools/{tool-name}/requirements.txt for each directory
RUN for dir in tools/*/; do \
      req="${dir}requirements.txt"; \
      if [ -f "$req" ]; then \
        echo "Installing deps for $(basename $dir)..."; \
        pip install --no-cache-dir -r "$req" || true; \
      fi; \
    done

# Copy the runner
COPY runner.py .

# Set tools directory
ENV TOOLS_DIR=/app/tools

EXPOSE 9080

CMD ["uvicorn", "runner:app", "--host", "0.0.0.0", "--port", "9080"]
