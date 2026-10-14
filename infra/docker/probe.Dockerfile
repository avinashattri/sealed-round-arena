FROM python:3.12-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl dnsutils iputils-ping iptables netcat-openbsd procps iproute2 && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /
COPY infra/probes /probes

CMD ["sleep", "infinity"]
