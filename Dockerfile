# The test suite with Python, its packages and Chromium, ready to run against the live site.
#   docker build -t aqx-tests .
#   docker run --rm --env-file .env -v "$PWD/allure-results:/app/allure-results" aqx-tests -m smoke
# Anything after the image name goes to pytest. The decryption key (AQX_ENCRYPTION_KEY) is passed in
# when the container runs, never built into the image.
FROM python:3.12-slim-bookworm

WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt \
    && playwright install --with-deps chromium

COPY . .

ENTRYPOINT ["pytest"]
