import socket
import ssl
import threading
from pathlib import Path

HOST = "10.5.25.223"
PORT = 5000

SECURITY_DIR = Path(__file__).resolve().parents[1] / "security"
CA_FILE = SECURITY_DIR / "certs" / "ca.crt"


def receive_messages(sock):
    while True:
        try:
            message = sock.recv(1024).decode()
            if not message:
                break
            print(message)
        except:
            print("Disconnected from server.")
            break


def start_client():
    raw_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    # TLS setup
    context = ssl.create_default_context()
    context.check_hostname = False
    context.verify_mode = ssl.CERT_NONE

    client = context.wrap_socket(raw_socket, server_hostname=HOST)
    client.connect((HOST, PORT))

    print(f"Connected with TLS cipher: {client.cipher()}")

    # start background thread to receive quiz messages
    thread = threading.Thread(target=receive_messages, args=(client,), daemon=True)
    thread.start()

    while True:
        answer = input()

        if answer.lower() == "quit":
            break

        client.send(answer.encode())

    client.close()


if __name__ == "__main__":
    start_client()