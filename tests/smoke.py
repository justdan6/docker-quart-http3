"""Run inside a started image: docker exec -i CONTAINER python - < tests/smoke.py."""

import asyncio
import http.client
import json
import os
import socket
import ssl
import time

import h2.config
import h2.connection
import h2.events
from aioquic.asyncio import QuicConnectionProtocol, connect
from aioquic.h3.connection import H3_ALPN, H3Connection
from aioquic.h3.events import DataReceived, HeadersReceived
from aioquic.quic.configuration import QuicConfiguration
from wsproto import ConnectionType, WSConnection
from wsproto.events import AcceptConnection, CloseConnection, Request, TextMessage


HOST = "127.0.0.1"
CERTFILE = os.environ.get("TLS_CERTFILE", "/home/quart/cert.pem")
ALT_SVC = f'h3=":{os.environ.get("HTTP3_PORT", "443")}"; ma=86400'


def wait_for_server():
    deadline = time.monotonic() + 30
    while True:
        try:
            with socket.create_connection((HOST, 443), timeout=1):
                return
        except OSError:
            if time.monotonic() >= deadline:
                raise
            time.sleep(0.2)


def check_http(tls=False):
    if tls:
        connection = http.client.HTTPSConnection(
            HOST, 443, context=ssl.create_default_context(cafile=CERTFILE), timeout=5
        )
    else:
        connection = http.client.HTTPConnection(HOST, 80, timeout=5)
    try:
        for path in ("/", "/api"):
            connection.request("GET", path)
            response = connection.getresponse()
            body = response.read()
            assert response.status == 200, (path, response.status)
            assert response.getheader("alt-svc") == ALT_SVC
            if path == "/api":
                assert json.loads(body) == {"hello": "world"}
            else:
                assert b"Hello World!" in body
    finally:
        connection.close()
    print("HTTPS HTTP/1.1 OK" if tls else "HTTP/1.1 OK", flush=True)


def check_http2():
    context = ssl.create_default_context(cafile=CERTFILE)
    context.set_alpn_protocols(["h2"])
    with socket.create_connection((HOST, 443), timeout=5) as raw:
        with context.wrap_socket(raw, server_hostname=HOST) as connection:
            assert connection.selected_alpn_protocol() == "h2"
            protocol = h2.connection.H2Connection(
                config=h2.config.H2Configuration(client_side=True, header_encoding="utf-8")
            )
            protocol.initiate_connection()
            protocol.send_headers(
                1,
                [(":method", "GET"), (":scheme", "https"),
                 (":authority", "localhost"), (":path", "/api")],
                end_stream=True,
            )
            connection.sendall(protocol.data_to_send())
            body = bytearray()
            headers = {}
            while True:
                data = connection.recv(65536)
                assert data, "HTTP/2 connection closed before response completed"
                for event in protocol.receive_data(data):
                    if isinstance(event, h2.events.ResponseReceived):
                        headers = dict(event.headers)
                    elif isinstance(event, h2.events.DataReceived):
                        body.extend(event.data)
                        protocol.acknowledge_received_data(event.flow_controlled_length, event.stream_id)
                    elif isinstance(event, h2.events.StreamEnded):
                        assert headers[":status"] == "200"
                        assert headers["alt-svc"] == ALT_SVC
                        assert json.loads(body) == {"hello": "world"}
                        print("HTTP/2 OK", flush=True)
                        return
                connection.sendall(protocol.data_to_send())


class Http3Client(QuicConnectionProtocol):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.http = H3Connection(self._quic)
        self.response = asyncio.get_running_loop().create_future()
        self.headers = {}
        self.body = bytearray()

    def quic_event_received(self, event):
        for http_event in self.http.handle_event(event):
            if isinstance(http_event, HeadersReceived):
                self.headers.update(dict(http_event.headers))
            elif isinstance(http_event, DataReceived):
                self.body.extend(http_event.data)
            if isinstance(http_event, (HeadersReceived, DataReceived)):
                if http_event.stream_ended and not self.response.done():
                    self.response.set_result((self.headers, self.body))

    async def get(self):
        stream_id = self._quic.get_next_available_stream_id()
        self.http.send_headers(
            stream_id,
            [(b":method", b"GET"), (b":scheme", b"https"),
             (b":authority", b"localhost"), (b":path", b"/api")],
            end_stream=True,
        )
        self.transmit()
        return await asyncio.wait_for(self.response, timeout=10)


async def check_http3():
    configuration = QuicConfiguration(is_client=True, alpn_protocols=H3_ALPN)
    configuration.load_verify_locations(CERTFILE)
    configuration.server_name = "localhost"
    async with asyncio.timeout(15):
        async with connect(HOST, 443, configuration=configuration, create_protocol=Http3Client) as client:
            headers, body = await client.get()
            assert headers[b":status"] == b"200"
            assert headers[b"alt-svc"].decode() == ALT_SVC
            assert json.loads(body) == {"hello": "world"}
    print("HTTP/3 over QUIC/UDP OK", flush=True)


def check_websocket(tls=False):
    raw = socket.create_connection((HOST, 443 if tls else 80), timeout=5)
    if tls:
        context = ssl.create_default_context(cafile=CERTFILE)
        connection = context.wrap_socket(raw, server_hostname=HOST)
    else:
        connection = raw
    with connection:
        protocol = WSConnection(ConnectionType.CLIENT)
        connection.sendall(protocol.send(Request(host="localhost", target="/ws")))
        accepted = False
        messages = []
        message = ""
        while len(messages) < 2:
            data = connection.recv(65536)
            assert data, "WebSocket closed before both messages arrived"
            protocol.receive_data(data)
            for event in protocol.events():
                if isinstance(event, AcceptConnection):
                    accepted = True
                elif isinstance(event, TextMessage):
                    message += event.data
                    if event.message_finished:
                        messages.append(message)
                        message = ""
                elif isinstance(event, CloseConnection):
                    raise AssertionError(f"WebSocket closed early: {event}")
        assert accepted
        assert messages[0] == "hello"
        assert json.loads(messages[1]) == {"hello": "world"}
        connection.sendall(protocol.send(CloseConnection(code=1000)))
    print("WSS OK" if tls else "WebSocket OK", flush=True)


wait_for_server()
check_http()
check_http(tls=True)
check_http2()
asyncio.run(check_http3())
check_websocket()
check_websocket(tls=True)
