import socket
import threading
import ssl
import csv
import time
import random
import sys
import tkinter as tk
from tkinter import messagebox
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
        self.root.title("Secure Quiz Server - Live Spectator Dashboard")
        self.root.geometry("800x650")
        self.root.configure(bg="#ffffff")

        self.clients = []
        self.scores = {}
        self.answers = {}
        self.lock = threading.Lock()
        
        # Admin Control Flags
        self.quiz_active = False
        self.quiz_ended = False
        self.q_idx = 0

        # Setup Variables
        self.question_timer = 20  
        self.lb_freq = 1
        
        # Load all questions first
        self.all_questions = self.load_questions()
        self.questions = []

        # Start background network listener immediately
        threading.Thread(target=self.start_network, daemon=True).start()
        
        # Start the background game loop (it will sleep until setup is applied)
        threading.Thread(target=self.quiz_loop, daemon=True).start()

        # Build the initial Setup GUI
        self.build_setup_gui()

    # ==========================================
    # GUI BUILDERS
    # ==========================================
    def build_setup_gui(self):
        """Draws the initial Setup Wizard screen."""
        self.setup_frame = tk.Frame(self.root, bg="#ffffff")
        self.setup_frame.pack(pady=40, fill=tk.BOTH, expand=True)

        tk.Label(self.setup_frame, text="Quiz Setup Wizard", font=("Helvetica", 22, "bold"), bg="#ffffff").pack(pady=20)

        max_q = len(self.all_questions)

        # Question Count
        tk.Label(self.setup_frame, text=f"How many questions to ask? (Max {max_q}):", font=("Helvetica", 14), bg="#ffffff").pack(pady=5)
        self.entry_num_q = tk.Entry(self.setup_frame, font=("Helvetica", 14), width=15, justify="center")
        self.entry_num_q.insert(0, str(min(5, max_q))) 
        self.entry_num_q.pack(pady=5)

        # Timer
        tk.Label(self.setup_frame, text="Time limit per question (seconds):", font=("Helvetica", 14), bg="#ffffff").pack(pady=5)
        self.entry_timer = tk.Entry(self.setup_frame, font=("Helvetica", 14), width=15, justify="center")
        self.entry_timer.insert(0, "20")
        self.entry_timer.pack(pady=5)

        # Leaderboard Frequency
        tk.Label(self.setup_frame, text="Show leaderboard every X questions:", font=("Helvetica", 14), bg="#ffffff").pack(pady=5)
        self.entry_lb_freq = tk.Entry(self.setup_frame, font=("Helvetica", 14), width=15, justify="center")
        self.entry_lb_freq.insert(0, "1")
        self.entry_lb_freq.pack(pady=5)

        tk.Button(self.setup_frame, text="Start Quiz Now", font=("Helvetica", 16, "bold"), 
                  bg="#28a745", fg="white", width=20, command=self.apply_setup).pack(pady=40)

    def apply_setup(self):
        """Reads setup inputs, hides setup frame, and reveals main dashboard."""
        try:
            num_q = int(self.entry_num_q.get())
            self.question_timer = int(self.entry_timer.get())
            self.lb_freq = int(self.entry_lb_freq.get())

            max_q = len(self.all_questions)
            num_q = min(max(1, num_q), max_q) 
            
            self.questions = self.all_questions[:num_q]

            # Reset game state
            self.q_idx = 0
            self.answers.clear()
            with self.lock:
                for client in self.clients:
                    self.scores[client] = 0

            # Switch GUI
            self.setup_frame.destroy()
            self.build_dashboard_gui()
            
            # Unpause the background game loop
            self.quiz_active = True
            self.quiz_ended = False

            self.update_lobby_display()
            self.update_live_leaderboard()

        except ValueError:
            messagebox.showerror("Invalid Input", "Please enter valid numbers for all fields.")

    def build_dashboard_gui(self):
        """Draws the main Live Spectator & Admin Dashboard."""
        self.dash_frame = tk.Frame(self.root, bg="#ffffff")
        self.dash_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)

        # Top Bar: Lobby & Timer
        top_frame = tk.Frame(self.dash_frame, bg="#ffffff")
        top_frame.pack(fill=tk.X, pady=10)
        
        self.lobby_label = tk.Label(top_frame, text="LOBBY: 0 Players", font=("Helvetica", 14, "bold"), fg="#007bff", bg="#ffffff")
        self.lobby_label.pack(side=tk.LEFT)

        self.timer_label = tk.Label(top_frame, text="Starting...", font=("Helvetica", 16, "bold"), fg="#d9534f", bg="#ffffff")
        self.timer_label.pack(side=tk.RIGHT)

        # Middle Section: Split Spectator and Leaderboard
        mid_frame = tk.Frame(self.dash_frame, bg="#ffffff")
        mid_frame.pack(fill=tk.BOTH, expand=True, pady=10)

        # Left: Spectator View
        spectator_frame = tk.LabelFrame(mid_frame, text=" Live Spectator View ", font=("Helvetica", 12, "bold"), bg="#f9f9f9", padx=10, pady=10)
        spectator_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 10))

        self.spectator_q_lbl = tk.Label(spectator_frame, text="Waiting for question...", font=("Helvetica", 14), bg="#f9f9f9", justify=tk.LEFT, wraplength=450)
        self.spectator_q_lbl.pack(anchor="w", pady=10)

        self.spectator_ans_lbl = tk.Label(spectator_frame, text="", font=("Helvetica", 16, "bold"), bg="#f9f9f9", fg="#28a745")
        self.spectator_ans_lbl.pack(anchor="center", pady=30)

        # Right: Live Leaderboard
        lb_frame = tk.LabelFrame(mid_frame, text=" Live Leaderboard ", font=("Helvetica", 12, "bold"), bg="#f9f9f9", padx=10, pady=10)
        lb_frame.pack(side=tk.RIGHT, fill=tk.Y)

        self.live_lb_lbl = tk.Label(lb_frame, text="No players yet.", font=("Helvetica", 12), bg="#f9f9f9", justify=tk.LEFT)
        self.live_lb_lbl.pack(anchor="nw")

        # Bottom: End Quiz Button
        self.end_btn = tk.Button(self.dash_frame, text="End Quiz Early", font=("Helvetica", 12, "bold"), 
                                 bg="#d9534f", fg="white", width=20, command=self.revert_to_setup)
        self.end_btn.pack(pady=10)

    # ==========================================
    # THREAD-SAFE GUI UPDATERS
    # ==========================================
    def update_gui_timer(self, text, color="black"):
        def _update():
            if hasattr(self, 'timer_label') and self.timer_label.winfo_exists():
                self.timer_label.config(text=text, fg=color)
        self.root.after(0, _update)

    def update_gui_spectator(self, q_text, ans_text=""):
        def _update():
            if hasattr(self, 'spectator_q_lbl') and self.spectator_q_lbl.winfo_exists():
                self.spectator_q_lbl.config(text=q_text.strip())
                self.spectator_ans_lbl.config(text=ans_text)
        self.root.after(0, _update)

    def update_lobby_display(self):
        def _update():
            if hasattr(self, 'lobby_label') and self.lobby_label.winfo_exists():
                self.lobby_label.config(text=f"LOBBY: {len(self.clients)} Player(s)")
        self.root.after(0, _update)

    def update_live_leaderboard(self):
        def _update():
            if hasattr(self, 'live_lb_lbl') and self.live_lb_lbl.winfo_exists():
                text = ""
                with self.lock:
                    # Sort scores descending
                    sorted_scores = sorted(self.scores.items(), key=lambda x: x[1], reverse=True)
                    for i, (client, score) in enumerate(sorted_scores):
                        text += f"Player {i+1}: {score} pts\n\n"
                
                if not text:
                    text = "No players yet."
                self.live_lb_lbl.config(text=text)
        self.root.after(0, _update)

    def revert_to_setup(self):
        """Ends the quiz, notifies clients, destroys dash, and rebuilds setup."""
        self.quiz_active = False
        self.quiz_ended = True
        self.broadcast("QUIZ_ENDED")
        
        if hasattr(self, 'dash_frame') and self.dash_frame.winfo_exists():
            self.dash_frame.destroy()
            
        self.build_setup_gui()

    # ==========================================
    # NETWORKING & GAME LOGIC
    # ==========================================
    def load_questions(self):
        questions = []
        try:
            with open(DATA_FILE, newline='', encoding="utf-8") as file:
                reader = csv.DictReader(file)
                for row in reader:
                    question_text = (
                        f"{row['Question']}\n\n"
                        f"A) {row['OptionA']}\n"
                        f"B) {row['OptionB']}\n"
                        f"C) {row['OptionC']}\n"
                        f"D) {row['OptionD']}"
                    )
                    correct_answer = row["Correct"].strip().upper()
                    questions.append((question_text, correct_answer))
            random.shuffle(questions)
        except Exception:
            pass
        return questions

    def broadcast(self, message):
        with self.lock:
            for client in self.clients:
                try:
                    client.send((message + "\n").encode())
                except:
                    pass

    def handle_client(self, conn, addr):
        with self.lock:
            self.clients.append(conn)
            self.scores[conn] = 0
        
        self.update_lobby_display()
        self.update_live_leaderboard()
        conn.send("Welcome to the Secure Quiz Server\n".encode())

        while True:
            try:
                data = conn.recv(1024)
                if not data:
                    break
                answer = data.decode().strip().upper()
                with self.lock:
                    self.answers[conn] = answer
            except:
                break

        with self.lock:
            if conn in self.clients:
                self.clients.remove(conn)
            if conn in self.scores:
                del self.scores[conn]
        
        self.update_lobby_display()
        self.update_live_leaderboard()
        conn.close()

    def quiz_loop(self):
        while True:
            # Sleep if waiting on Setup screen
            if not self.quiz_active or self.quiz_ended or len(self.clients) == 0:
                time.sleep(1)
                continue

            if self.q_idx >= len(self.questions):
                self.display_leaderboard()
                self.root.after(0, self.revert_to_setup)
                continue

            question, correct_answer = self.questions[self.q_idx]
            self.answers.clear()
            
            # Broadcast to clients & update local Spectator View
            self.broadcast(f"\nQUESTION|{self.question_timer}:\n" + question)
            self.update_gui_spectator(question, "")

            interrupted = False
            for remaining in range(self.question_timer, 0, -1):
                if not self.quiz_active or self.quiz_ended:
                    interrupted = True
                    break
                self.update_gui_timer(f"Time Left: {remaining}s", "#d9534f")
                time.sleep(1)

            if interrupted:
                continue

            # Evaluate scores + send per-client result
            with self.lock:
                for client in list(self.clients):
                    chosen = self.answers.get(client, "-")  # "-" means no answer
                    is_correct = (chosen == correct_answer)

                    if is_correct:
                        self.scores[client] += 10

                    if chosen == "-":
                        status = "NO_ANSWER"
                    elif is_correct:
                        status = "CORRECT"
                    else:
                        status = "WRONG"

                    try:
                        client.send(f"RESULT|{status}|{chosen}|{correct_answer}\n".encode())
                    except:
                        pass

            self.update_live_leaderboard()

            # 5-Second Reveal
            self.broadcast(f"CORRECT_ANSWER: {correct_answer}")
            self.update_gui_spectator(question, f"Correct Answer: {correct_answer}")
            
            for remaining in range(5, 0, -1):
                if self.quiz_ended: break
                self.update_gui_timer(f"Reveal: {remaining}s", "#28a745")
                time.sleep(1)

            if self.quiz_ended: continue

            # Periodic Leaderboard Check
            if (self.q_idx + 1) % self.lb_freq == 0 or (self.q_idx + 1) == len(self.questions):
                self.update_gui_timer("Displaying Leaderboard...", "#007bff")
                self.display_leaderboard()
            else:
                self.broadcast("WAITING\nGet ready for the next question...")
                self.update_gui_timer("Waiting for next question...", "gray")
                time.sleep(2)

            self.q_idx += 1

    def display_leaderboard(self):
        """Builds and broadcasts the leaderboard to clients."""
        leaderboard = "\n--- LEADERBOARD ---\n"
        with self.lock:
            # Sort scores descending
            sorted_scores = sorted(self.scores.items(), key=lambda x: x[1], reverse=True)
            for i, (client, score) in enumerate(sorted_scores):
                leaderboard += f"Player {i+1}: {score} pts\n"
        leaderboard += "-------------------\n"

        self.broadcast("LEADERBOARD\n" + leaderboard)
        
        for _ in range(3):
            if self.quiz_ended: break
            time.sleep(1)

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
            server.settimeout(1.0) 

            while True:
                try:
                    raw_conn, addr = server.accept()
                except socket.timeout:
                    continue
                except Exception:
                    break

                try:
                    tls_conn = context.wrap_socket(raw_conn, server_side=True)
                except ssl.SSLError:
                    raw_conn.close()
                    continue

                threading.Thread(target=self.handle_client, args=(tls_conn, addr), daemon=True).start()

        except Exception:
            pass

if __name__ == "__main__":
    root = tk.Tk()
    app = QuizServer(root)
    root.mainloop()