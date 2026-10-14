FROM python:3.12-slim

ARG COMPONENT=broker
ARG SRC=referee/broker
ARG PORT=8000
ARG BLUE_VERSION=""

ENV COMPONENT=${COMPONENT}
ENV PORT=${PORT}
ENV BLUE_VERSION=${BLUE_VERSION}
ENV PYTHONUNBUFFERED=1

RUN useradd -u 10001 -m -s /bin/bash appuser && \
    mkdir -p /sealed /data /app && \
    chown -R appuser:appuser /sealed /data /app

WORKDIR /app

COPY requirements/${COMPONENT}.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

COPY contracts/ /app/contracts/
COPY ${SRC}/ /app/${COMPONENT}/

ENV PYTHONPATH=/app

USER 10001

CMD ["sh", "-c", "exec uvicorn ${COMPONENT}.app:app --host 0.0.0.0 --port ${PORT}"]
