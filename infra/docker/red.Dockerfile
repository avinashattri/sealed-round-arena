FROM python:3.12-slim

RUN useradd -u 10001 -m -s /bin/bash appuser

WORKDIR /app

RUN pip install --no-cache-dir httpx pydantic

COPY contracts/ /app/contracts/
COPY loop/red/ /app/red/

ENV PYTHONPATH=/app

USER 10001

CMD ["sleep", "infinity"]
