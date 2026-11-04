# Quart with HTTP/3 in Docker

An example [Quart](https://quart.palletsprojects.com/) ASGI app served by
[Hypercorn](https://hypercorn.readthedocs.io/) over HTTP/1.1, HTTP/2, HTTP/3, and
WebSockets. Images support `linux/amd64` and `linux/arm64`.

The runtime uses Python **3.15.2**, Alpine **3.24**, Quart **0.23.1**, Hypercorn
**0.18.0**, and aioquic **1.7.2**. Python dependencies are pinned in
`requirements.txt`; operating-system packages come from the stable Alpine
repositories. Compiler packages and Alpine edge repositories are unnecessary.

## Run the published image

```sh
docker run -d --name quart-http3 \
  --restart unless-stopped --pull always \
  -e HTTP3_PORT=8443 \
  -p 8080:80/tcp \
  -p 8443:443/tcp \
  -p 8443:443/udp \
  justdanz/quart-http3:latest
```

Or run `./run-docker.sh` from this repository. Optional environment variables for
that helper are `IMAGE`, `CONTAINER_NAME`, `HTTP_PORT` (default `8080`), and
`HTTPS_PORT` (default `8443`). The helper starts a named background container;
use `docker logs -f quart-http3` to see its logs.

Visit <http://localhost:8080> or <https://localhost:8443>. The `/api` endpoint
returns `{"hello":"world"}`, and `/ws` serves WebSockets.

A unique self-signed certificate for `localhost` and `127.0.0.1` is generated on
first startup, so the HTTPS example produces a browser certificate warning.
The same container keeps its certificate across restarts; replacing the
container generates a new one. The image contains no private key.

HTTP/3 needs **UDP** as well as TCP on the published HTTPS port. Set
`HTTP3_PORT` to that external UDP port so the `Alt-Svc` response header points
clients to the correct port. Its default is `443`; the example sets `8443`.
For public hosting, publish port `443` for both TCP and UDP, set `HTTP3_PORT=443`,
and allow the chosen ports through your firewall.

## Update an existing container

After the updated image has been published, pull it **before** stopping the old
container, then recreate the container with the same settings:

```sh
docker pull justdanz/quart-http3:latest
docker stop quart-http3
docker rm quart-http3
docker run -d --name quart-http3 \
  --restart unless-stopped \
  -e HTTP3_PORT=8443 \
  -p 8080:80/tcp \
  -p 8443:443/tcp \
  -p 8443:443/udp \
  justdanz/quart-http3:latest
```

Substitute your existing container name if different, and preserve any custom
ports, environment variables, and certificate mounts. `docker restart` alone
does not adopt a newly pulled image. If you already manage this image with
Docker Compose, run `docker compose pull && docker compose up -d` from your
Compose project instead, ensuring its port mappings include UDP and its
`HTTP3_PORT` matches the published port.

## Build and test locally

```sh
git clone https://github.com/justdan6/docker-quart-http3.git
cd docker-quart-http3
docker build --pull --no-cache -t quart-http3:local .
docker run -d --name quart-http3-test -e HTTP3_PORT=8443 quart-http3:local
docker exec -i quart-http3-test python - < tests/smoke.py
docker logs quart-http3-test
docker rm -f quart-http3-test
```

The smoke test makes real HTTP/1.1, HTTPS, HTTP/2, HTTP/3 over QUIC/UDP,
WebSocket, and secure WebSocket requests inside the running container. It
verifies response bodies and the advertised HTTP/3 port, using the generated
certificate as its trust root. It requires no additional test packages.

To test HTTP/3 through the host's published port with a curl build that lists
`HTTP3` in `curl --version`:

```sh
curl --http3-only --insecure https://localhost:8443/api
```

`--insecure` is for the example self-signed certificate. Use a trusted
certificate for public hosting.

## Publish an updated image

The GitHub Actions workflow tests both image architectures on pull requests.
A push or merge to `main` tests them again, then publishes:

- `justdanz/quart-http3:latest`
- `justdanz/quart-http3:sha-<full-commit-sha>` for rollback to a specific build

Publishing requires the repository Actions secrets `DOCKERHUB_USERNAME` and
`DOCKERHUB_TOKEN`, with the token allowed to push `justdanz/quart-http3`.
To rebuild the current `main` without a code change, use **Actions → Build,
test, and publish Docker image → Run workflow**, or:

```sh
gh workflow run push-to-docker-hub.yml --repo justdan6/docker-quart-http3 --ref main
```

Alternatively, publish manually after logging in to Docker Hub:

```sh
docker login
docker buildx build --pull --no-cache \
  --platform linux/amd64,linux/arm64 \
  -t justdanz/quart-http3:latest --push .
```

The manual command requires a Buildx builder with multi-platform support.
Dependabot checks Python packages and the Docker base image daily, and GitHub
Actions weekly. Merge its tested updates and recreate deployed containers to
apply them.

## Supply your own TLS certificate

Set `TLS_CERTFILE` and `TLS_KEYFILE` to existing certificate and key files
mounted read-only into the container. For example, add these options to
`docker run` before the image name:

```sh
--mount type=bind,src=/absolute/path/to/tls,dst=/tls,readonly \
-e TLS_CERTFILE=/tls/fullchain.pem \
-e TLS_KEYFILE=/tls/privkey.pem
```

Both files must be readable by the container's `quart` user (UID/GID `1000`).
Restart the container after renewing mounted certificates. Hypercorn's runtime
configuration is in `src/hypercorn_config.py`.
