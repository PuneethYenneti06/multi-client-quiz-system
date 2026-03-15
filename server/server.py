import socket
import threading

HOST = "0.0.0.0"
PORT = 5000


def handle_client(conn, addr):
    print(f"Client connected: {addr}")

    conn.send("Welcome to the Quiz Server\n".encode())

    while True:
        try:
            data = conn.recv(1024)

            if not data:
                break

            print(f"Received from {addr}: {data.decode()}")

        except:
            break

    print(f"Client disconnected: {addr}")
    conn.close()


def start_server():
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    server.bind((HOST, PORT))
    server.listen()

    print("Quiz server running...")

    while True:
        conn, addr = server.accept()

        thread = threading.Thread(target=handle_client, args=(conn, addr))
        thread.start()


start_server()