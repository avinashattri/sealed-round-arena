FROM python:3.12-slim

RUN useradd -u 10001 -m -s /bin/bash appuser

WORKDIR /app
COPY infra/docker/stub/stub.py /app/stub.py

USER 10001

CMD ["python", "/app/stub.py"]
