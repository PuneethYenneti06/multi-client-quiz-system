import socket
import threading
import ssl
import csv
import time
import random
import tkinter as tk
from pathlib import Path

HOST = "0.0.0.0"
PORT = 5000

SECURITY_DIR = Path(__file__).resolve().parents[1] / "security"
CERT_FILE = SECURITY_DIR / "certs" / "server.crt"
KEY_FILE = SECURITY_DIR / "certs" / "server.key"

DATA_FILE = Path(__file__).resolve().parents[1] / "data" / "questions.csv"


class QuizServer:
    def __init__(self, root):
        self.root = root
        self.root.title("Secure Quiz Server Admin")
        self.root.geometry("700x550")
        self.root.configure(bg="#ffffff")

        # --- Server State Variables ---
        self.clients = []
        self.scores = {}
        self.answers = {}
        self.lock = threading.Lock()
        self.quiz_active = False

        # --- GUI Elements ---
        self.header = tk.Label(root, text="Server Admin Dashboard", bg="#ffffff", font=("Helvetica", 18, "bold"))
        self.header.pack(pady=10)

        # Control Button
        self.start_btn = tk.Button(root, text="Start Quiz", font=("Helvetica", 14, "bold"), 
                                   bg="#28a745", fg="white", width=20, command=self.toggle_quiz)
        self.start_btn.pack(pady=10)

        # Log Console
        self.log_area = tk.Text(root, height=20, width=80, font=("Courier", 10), bg="#f4f4f4", state=tk.DISABLED)
        self.log_area.pack(pady=10)

        # --- Initialization ---
        self.questions = self.load_questions()

        # Start background threads for networking and the quiz loop
        threading.Thread(target=self.start_network, daemon=True).start()
        threading.Thread(target=self.quiz_loop, daemon=True).start()

    def log(self, message):
        """Thread-safe way to print messages to the GUI console."""
        self.root.after(0, self._append_log, message)

    def _append_log(self, message):
        self.log_area.config(state=tk.NORMAL)
        self.log_area.insert(tk.END, message + "\n")
        self.log_area.see(tk.END)  # Auto-scroll to the bottom
        self.log_area.config(state=tk.DISABLED)

    def toggle_quiz(self):
        """Allows the admin to manually start or pause the question loop."""
        self.quiz_active = not self.quiz_active
        if self.quiz_active:
            self.start_btn.config(text="Pause Quiz", bg="#ffc107", fg="black")
            self.log("\n>>> QUIZ STARTED: Broadcasting questions... <<<")
        else:
            self.start_btn.config(text="Start Quiz", bg="#28a745", fg="white")
            self.log("\n>>> QUIZ PAUSED <<<")

    def load_questions(self):
        questions = []
        try:
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
            self.log(f"Loaded {len(questions)} questions from CSV.")
        except Exception as e:
            self.log(f"Error loading questions: {e}")
        return questions

    def broadcast(self, message):
        with self.lock:
            for client in self.clients:
                try:
                    client.send((message + "\n").encode())
                except:
                    pass

    def handle_client(self, conn, addr):
        self.log(f"Client connected: {addr} | Cipher: {conn.cipher()[0]}")
        conn.send("Welcome to the Secure Quiz Server\n".encode())

        with self.lock:
            self.clients.append(conn)
            self.scores[conn] = 0

        while True:
            try:
                data = conn.recv(1024)
                if not data:
                    break
                answer = data.decode().strip().upper()
                with self.lock:
                    self.answers[conn] = answer
                self.log(f"Received locked answer from {addr}")
            except:
                break

        self.log(f"Client disconnected: {addr}")
        with self.lock:
            if conn in self.clients:
                self.clients.remove(conn)
            if conn in self.scores:
                del self.scores[conn]
        conn.close()

    def quiz_loop(self):
        while True:
            # Wait if the admin hasn't clicked "Start" or if there are no players
            if not self.quiz_active or len(self.clients) == 0:
                time.sleep(1)
                continue

            for question, correct_answer in self.questions:
                if not self.quiz_active:
                    break  # Break out if admin pauses mid-quiz

                self.answers.clear()
                self.broadcast("\nQUESTION:\n" + question)
                self.log("Broadcasted new question. Waiting 20 seconds for answers...")
                time.sleep(20)

                with self.lock:
                    for client, answer in self.answers.items():
                        if answer == correct_answer:
                            self.scores[client] += 10

                # --- NEW 5-SECOND REVEAL LOGIC ---
                self.broadcast(f"CORRECT_ANSWER: {correct_answer}")
                self.log(f"Time's up! Revealed correct answer: {correct_answer}. Pausing for 5 seconds...")
                time.sleep(5)
                # ---------------------------------

                leaderboard = "\nLEADERBOARD\n"
                with self.lock:
                    for i, (client, score) in enumerate(self.scores.items()):
                        # We use Player indices until usernames are implemented
                        leaderboard += f"Player {i+1}: {score}\n"

                self.broadcast(leaderboard)
                self.log("Broadcasted leaderboard.")
                time.sleep(3)
                
            # If all questions are done, auto-pause
            if self.quiz_active:
                self.log("\n>>> End of Question Bank Reached <<<")
                self.toggle_quiz()

    def start_network(self):
        try:
            context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
            context.minimum_version = ssl.TLSVersion.TLSv1_2
            context.load_cert_chain(certfile=str(CERT_FILE), keyfile=str(KEY_FILE))
            context.verify_mode = ssl.CERT_NONE

            server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            server.bind((HOST, PORT))
            server.listen()
            server.settimeout(1.0) # Allows the thread to check for shutdown

            self.log(f"Secure server listening on {HOST}:{PORT}")

            while True:
                try:
                    raw_conn, addr = server.accept()
                except socket.timeout:
                    continue
                except Exception as e:
                    self.log(f"Server acceptance error: {e}")
                    break

                try:
                    tls_conn = context.wrap_socket(raw_conn, server_side=True)
                except ssl.SSLError as e:
                    self.log(f"TLS handshake failed from {addr}: {e}")
                    raw_conn.close()
                    continue

                # Pass to client handler thread
                threading.Thread(target=self.handle_client, args=(tls_conn, addr), daemon=True).start()

        except Exception as e:
            self.log(f"CRITICAL: Failed to start server network: {e}")


if __name__ == "__main__":
    root = tk.Tk()
    app = QuizServer(root)
    root.mainloop()