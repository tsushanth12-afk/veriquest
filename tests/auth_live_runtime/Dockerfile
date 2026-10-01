FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt
COPY service.py /app/runtime/service.py
ENV PYTHONDONTWRITEBYTECODE=1 VQ_AUTH_BACKEND_PATH=/app/backend
USER 1000:1000
CMD ["python", "/app/runtime/service.py", "--host", "0.0.0.0", "--port", "8080"]
