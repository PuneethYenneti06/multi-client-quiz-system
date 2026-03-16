import socket
import threading
import ssl
from pathlib import Path

HOST = "0.0.0.0"
PORT = 5000

SECURITY_DIR = Path(__file__).resolve().parents[1] / "security"
CA_FILE = SECURITY_DIR / "certs" / "ca.crt"
CERT_FILE = SECURITY_DIR / "certs" / "server.crt"
KEY_FILE = SECURITY_DIR / "certs" / "server.key"


def handle_client(conn, addr):
    print(f"Client connected: {addr}")
    print(f"TLS cipher: {conn.cipher()}")

    conn.send("Welcome to the Secure Quiz Server\n".encode())

    while True:
        try:
            data = conn.recv(1024)
            if not data:
                break
            print(f"Received from {addr}: {data.decode()}")
        except Exception:
            break

    print(f"Client disconnected: {addr}")
    conn.close()


def start_server():
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.minimum_version = ssl.TLSVersion.TLSv1_2
    context.load_cert_chain(certfile=str(CERT_FILE), keyfile=str(KEY_FILE))
    context.load_verify_locations(cafile=str(CA_FILE))

    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind((HOST, PORT))
    server.listen()

    print("Secure quiz server running...")

    while True:
        raw_conn, addr = server.accept()
        try:
            tls_conn = context.wrap_socket(raw_conn, server_side=True)
        except ssl.SSLError as e:
            print(f"TLS handshake failed from {addr}: {e}")
            raw_conn.close()
            continue

        thread = threading.Thread(target=handle_client, args=(tls_conn, addr), daemon=True)
        thread.start()


start_server()