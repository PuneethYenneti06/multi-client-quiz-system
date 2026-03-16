import socket
import ssl
from pathlib import Path

HOST = "10.5.25.223"
PORT = 5000

SECURITY_DIR = Path(__file__).resolve().parents[1] / "security"
CA_FILE = SECURITY_DIR / "certs" / "ca.crt"


def start_client():
    raw_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
#Certificate Authority (CA)
    context = ssl.create_default_context()
    context.check_hostname = False
    context.verify_mode = ssl.CERT_NONE

    client = context.wrap_socket(raw_socket, server_hostname=HOST)
    client.connect((HOST, PORT))

    print(f"Connected with TLS cipher: {client.cipher()}")

    message = client.recv(1024)
    print(message.decode())

    while True:
        msg = input("Enter message (type 'quit' to exit): ")
        if msg.lower() == "quit":
            break
        client.send(msg.encode())

    client.close()


start_client()
