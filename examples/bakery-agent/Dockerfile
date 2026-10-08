FROM python:3.12-slim
WORKDIR /workspace
COPY requirements.lock .
RUN pip install --no-cache-dir -r requirements.lock
COPY scripts scripts
COPY services services
COPY configs configs
COPY knowledge knowledge
CMD ["python", "scripts/agent_http_api.py", "--host", "0.0.0.0", "--port", "8765", "--timeout", "360"]
