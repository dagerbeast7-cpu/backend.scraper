FROM mcr.microsoft.com/playwright/python:v1.47.0-jammy

WORKDIR /code

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Playwright browser binaries are already included in the official image
# RUN playwright install --with-deps chromium

COPY . .

CMD ["uvicorn", "app.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
