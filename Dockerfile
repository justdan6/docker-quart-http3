FROM python:3.15.2-alpine3.24

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN apk upgrade --no-cache \
    && apk add --no-cache openssl \
    && adduser -D quart

WORKDIR /home/quart

COPY requirements.txt ./
RUN python -m pip install --no-cache-dir --upgrade pip==26.3 \
    && python -m pip install --no-cache-dir --only-binary=:all: -r requirements.txt \
    && python -m pip check

COPY --chown=quart:quart src/ ./
COPY --chmod=755 docker-entrypoint.sh /usr/local/bin/docker-entrypoint.sh

EXPOSE 80/tcp 443/tcp 443/udp

USER quart
ENTRYPOINT ["docker-entrypoint.sh"]
CMD ["hypercorn", "--config", "file:hypercorn_config.py", "app:app"]
