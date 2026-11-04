import os

accesslog = "-"
errorlog = "-"
insecure_bind = ["0.0.0.0:80"]
bind = ["0.0.0.0:443"]
quic_bind = ["0.0.0.0:443"]
certfile = os.environ.get("TLS_CERTFILE", "/home/quart/cert.pem")
keyfile = os.environ.get("TLS_KEYFILE", "/home/quart/key.pem")

# Advertise the externally published UDP port, which may differ from port 443.
http3_port = int(os.environ.get("HTTP3_PORT", "443"))
if not 1 <= http3_port <= 65535:
    raise ValueError("HTTP3_PORT must be between 1 and 65535")
alt_svc_headers = [f'h3=":{http3_port}"; ma=86400']
