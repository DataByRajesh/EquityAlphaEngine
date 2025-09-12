FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app
EXPOSE 8080
CMD ["sh", "-c", "echo PORT=$PORT; uvicorn web.api:app --host 0.0.0.0 --port ${PORT:-8080}"]
