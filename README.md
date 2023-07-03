# What is this?
An example [ASGI](https://asgi.readthedocs.io/en/latest/) python web app using [quart](https://quart.palletsprojects.com/en/latest/) and [hypercorn](https://pgjones.gitlab.io/hypercorn/index.html) with HTTP3 support.

# How to use this image
```
docker pull justdanz/quart-http3:latest

docker run -it -p 0.0.0.0:8080:80 -p 0.0.0.0:8443:443/tcp -p 0.0.0.0:8443:443/udp -t justdanz/quart-http3:latest
```
Visit https://127.0.0.1:8443
