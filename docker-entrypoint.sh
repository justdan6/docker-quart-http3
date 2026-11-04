#!/bin/sh
set -eu

certfile="${TLS_CERTFILE:-/home/quart/cert.pem}"
keyfile="${TLS_KEYFILE:-/home/quart/key.pem}"

if [ ! -f "$certfile" ] || [ ! -f "$keyfile" ]; then
    if [ "$certfile" != /home/quart/cert.pem ] || [ "$keyfile" != /home/quart/key.pem ]; then
        echo "TLS_CERTFILE and TLS_KEYFILE must point to existing, readable certificate files." >&2
        exit 1
    fi

    # Generate a separate development key for each container, never in the image.
    umask 077
    openssl req -x509 -newkey rsa:2048 -nodes -days 365 \
        -keyout "$keyfile" -out "$certfile" \
        -subj /CN=localhost \
        -addext 'subjectAltName=DNS:localhost,IP:127.0.0.1'
fi

exec "$@"
