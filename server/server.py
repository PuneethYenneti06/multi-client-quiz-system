import socket
import threading
import ssl
import csv
import time
import random
from pathlib import Path

HOST = "0.0.0.0"
PORT = 5000

SECURITY_DIR = Path(__file__).resolve().parents[1] / "security"
CERT_FILE = SECURITY_DIR / "certs" / "server.crt"
KEY_FILE = SECURITY_DIR / "certs" / "server.key"

DATA_FILE = Path(__file__).resolve().parents[1] / "data" / "questions.csv"

clients = []
scores = {}
answers = {}

lock = threading.Lock()


def load_questions():
    questions = []

    with open(DATA_FILE, newline='', encoding="utf-8") as file:
        reader = csv.DictReader(file)

        for row in reader:
            question_text = (
                f"{row['Question']}\n"
                f"A) {row['OptionA']}\n"
                f"B) {row['OptionB']}\n"
                f"C) {row['OptionC']}\n"
                f"D) {row['OptionD']}"
            )

            correct_answer = row["Correct"].strip().upper()

            questions.append((question_text, correct_answer))

    random.shuffle(questions)

    return questions


questions = load_questions()


def broadcast(message):
    with lock:
        for client in clients:
            try:
                client.send((message + "\n").encode())
            except:
                pass


def handle_client(conn, addr):
    print(f"Client connected: {addr}")
    print(f"TLS cipher: {conn.cipher()}")

    conn.send("Welcome to the Secure Quiz Server\n".encode())

    with lock:
        clients.append(conn)
        scores[conn] = 0

    while True:
        try:
            data = conn.recv(1024)

            if not data:
                break

            answer = data.decode().strip().upper()

            with lock:
                answers[conn] = answer

        except:
            break

    print(f"Client disconnected: {addr}")

    with lock:
        if conn in clients:
            clients.remove(conn)
        if conn in scores:
            del scores[conn]

    conn.close()


def quiz_loop():

    while True:

        if len(clients) == 0:
            time.sleep(1)
            continue

        for question, correct_answer in questions:

            answers.clear()

            broadcast("\nQUESTION:\n" + question)
            print("Sent question")

            time.sleep(20)

            with lock:
                for client, answer in answers.items():
                    if answer == correct_answer:
                        scores[client] += 10

            leaderboard = "\nLEADERBOARD\n"

            with lock:
                for i, (client, score) in enumerate(scores.items()):
                    leaderboard += f"Player{i+1}: {score}\n"

            broadcast(leaderboard)

            time.sleep(3)


def start_server():

    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.minimum_version = ssl.TLSVersion.TLSv1_2
    context.load_cert_chain(certfile=str(CERT_FILE), keyfile=str(KEY_FILE))
    context.verify_mode = ssl.CERT_NONE

    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    server.bind((HOST, PORT))
    server.listen()
    server.settimeout(1.0)

    print("Secure quiz server running... Press Ctrl+C to stop.")

    threading.Thread(target=quiz_loop, daemon=True).start()

    try:
        while True:
            try:
                raw_conn, addr = server.accept()
            except socket.timeout:
                continue

            try:
                tls_conn = context.wrap_socket(raw_conn, server_side=True)
            except ssl.SSLError as e:
                print(f"TLS handshake failed from {addr}: {e}")
                raw_conn.close()
                continue

            thread = threading.Thread(target=handle_client, args=(tls_conn, addr), daemon=True)
            thread.start()

    except KeyboardInterrupt:
        print("\nShutting down server...")
    finally:
        server.close()


if __name__ == "__main__":
    start_server()