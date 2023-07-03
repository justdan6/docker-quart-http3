#!/bin/sh
docker run --rm -p 0.0.0.0:8080:80 -p 0.0.0.0:8443:443/tcp -p 0.0.0.0:8443:443/udp -t justdanz/quart-http3:latest