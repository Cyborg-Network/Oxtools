FROM python:3.11-slim

WORKDIR /app

# Install Python dependencies before copying application code.
# This layer is cached as long as requirements.txt is unchanged.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install Playwright system dependencies and the Chromium browser binary.
# This must run after pip install so the playwright CLI is on PATH.
RUN playwright install --with-deps chromium

# Copy the rest of the application source.
COPY . .

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
