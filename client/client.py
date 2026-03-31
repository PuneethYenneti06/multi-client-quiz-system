import socket
import ssl
import threading
import tkinter as tk
import sys
from pathlib import Path

# HOST = "10.5.25.223"
HOST = "127.0.0.1"
PORT = 5000

SECURITY_DIR = Path(__file__).resolve().parents[1] / "security"
CA_FILE = SECURITY_DIR / "certs" / "ca.crt"


class QuizClient:
    def __init__(self, root):
        self.root = root
        self.root.title("Secure Quiz Client")
        self.root.geometry("600x550")
        self.root.configure(bg="#ffffff")

        # --- GUI Elements ---
        self.header = tk.Label(root, text="Secure TLS Quiz", bg="#ffffff", font=("Helvetica", 18, "bold"))
        self.header.pack(pady=10)

        # Timer Label 
        self.timer_label = tk.Label(root, text="Waiting for game to start...", font=("Helvetica", 16, "bold"), bg="#ffffff", fg="gray")
        self.timer_label.pack()

        # Main text area
        self.display_text = tk.Text(root, height=10, width=60, font=("Helvetica", 12), bg="#f9f9f9", state=tk.DISABLED, wrap=tk.WORD)
        self.display_text.pack(pady=10)

        # Feedback Label
        self.feedback_label = tk.Label(root, text="Waiting for connection...", bg="#ffffff", font=("Helvetica", 14, "bold"), fg="gray")
        self.feedback_label.pack(pady=10)

        # Multiple Choice Buttons
        self.btn_frame = tk.Frame(root, bg="#ffffff")
        self.btn_frame.pack(pady=10)

        self.buttons = {}
        for opt in ['A', 'B', 'C', 'D']:
            btn = tk.Button(self.btn_frame, text=f"Option {opt}", font=("Helvetica", 12, "bold"), width=10,
                            command=lambda o=opt: self.send_answer(o), state=tk.DISABLED, bg="#e0e0e0")
            btn.pack(side=tk.LEFT, padx=10)
            self.buttons[opt] = btn

        # Quit Button
        self.quit_btn = tk.Button(root, text="Quit Game", font=("Helvetica", 12, "bold"), bg="#d9534f", fg="white", width=20, command=self.quit_app)
        self.quit_btn.pack(pady=20)

        # --- Timer & Networking Variables ---
        self.time_left = 0
        self.timer_id = None
        self.timer_mode = "question"
        
        self.client_socket = None
        self.selected_answer = None
        self.connect_to_server()

    def quit_app(self):
        """Safely closes the connection and shuts down the client."""
        if self.client_socket:
            try:
                self.client_socket.close()
            except:
                pass
        self.root.quit()
        self.root.destroy()
        sys.exit(0)

    def start_local_timer(self, seconds, mode="question"):
        if self.timer_id:
            self.root.after_cancel(self.timer_id)
        self.time_left = seconds
        self.timer_mode = mode
        self.update_timer_tick()

    def update_timer_tick(self):
        if self.time_left > 0:
            color = "#d9534f" if self.timer_mode == "question" else "#28a745"
            prefix = "Time Left" if self.timer_mode == "question" else "Next in"
            self.timer_label.config(text=f"{prefix}: {self.time_left}s", fg=color)
            
            self.time_left -= 1
            self.timer_id = self.root.after(1000, self.update_timer_tick)
        else:
            self.timer_label.config(text="Time's Up!" if self.timer_mode == "question" else "Loading...", fg="gray")

    def connect_to_server(self):
        try:
            raw_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            context = ssl.create_default_context()
            context.check_hostname = False
            context.verify_mode = ssl.CERT_NONE

            self.client_socket = context.wrap_socket(raw_socket, server_hostname=HOST)
            self.client_socket.connect((HOST, PORT))

            self.update_display(f"Connected securely!\nCipher: {self.client_socket.cipher()[0]}")
            self.feedback_label.config(text="Ready to play", fg="blue")

            threading.Thread(target=self.receive_messages, daemon=True).start()
        except Exception as e:
            self.update_display(f"Connection failed: {e}")
            self.feedback_label.config(text="Error", fg="red")

    def receive_messages(self):
        while True:
            try:
                message = self.client_socket.recv(1024).decode()
                if not message:
                    break
                self.root.after(0, self.process_message, message)
            except:
                self.root.after(0, self.update_display, "Disconnected from server.")
                break

    def process_message(self, message):
        # 1) Personalized result first
        if "RESULT|" in message:
            result_line = None
            for line in message.splitlines():
                if line.startswith("RESULT|"):
                    result_line = line.strip()
                    break

            if result_line:
                payload = result_line.split("|")
                if len(payload) >= 4:
                    status = payload[1].strip()
                    your_ans = payload[2].strip()
                    correct_ans = payload[3].strip()

                    if status == "CORRECT":
                        self.feedback_label.config(
                            text=f"Correct. The correct answer is {correct_ans}",
                            fg="#28a745"
                        )
                    elif status == "WRONG":
                        self.feedback_label.config(
                            text=f"Wrong. The correct answer is {correct_ans}",
                            fg="#d9534f"
                        )
                    else:
                        self.feedback_label.config(
                            text=f"No answer submitted. The correct answer is {correct_ans}",
                            fg="#ff9800"
                        )
                self.disable_buttons()
                self.start_local_timer(5, "reveal")
                return

        

        # 3) QUESTION
        if "QUESTION|" in message:
            parts = message.split(":\n", 1)
            header = parts[0]
            q_text = parts[1] if len(parts) > 1 else ""
            
            try:
                time_limit = int(header.split("|")[1])
            except:
                time_limit = 20 
                
            self.update_display("QUESTION:\n" + q_text)
            self.feedback_label.config(text="Select your answer!", fg="black")
            self.enable_buttons()
            self.start_local_timer(time_limit, "question")
            
        # 4) LEADERBOARD
        elif "LEADERBOARD" in message:
            self.update_display(message)
            self.disable_buttons()
            if self.timer_id:
                self.root.after_cancel(self.timer_id)
            self.timer_label.config(text="Leaderboard", fg="#007bff")
            
        # 5) WAITING
        elif "WAITING" in message:
            self.update_display(message)
            self.disable_buttons()
            if self.timer_id:
                self.root.after_cancel(self.timer_id)
            self.timer_label.config(text="Get Ready", fg="#007bff")

        # 6) QUIZ_ENDED
        elif "QUIZ_ENDED" in message:
            self.update_display("\n\n--- QUIZ ENDED ---\n\nThe quiz has officially concluded. Thank you for playing!")
            self.feedback_label.config(text="Quiz Ended", fg="red")
            self.disable_buttons()
            if self.timer_id:
                self.root.after_cancel(self.timer_id)
            self.timer_label.config(text="Finished", fg="gray")

        else:
            self.update_display(message)

    def send_answer(self, choice):
        if self.client_socket:
            try:
                self.client_socket.send(choice.encode())
                self.feedback_label.config(text=f"Answer locked in: {choice}", fg="blue")
                self.disable_buttons() 
            except Exception as e:
                self.update_display(f"Error sending answer: {e}")

    def update_display(self, text):
        self.display_text.config(state=tk.NORMAL)
        self.display_text.delete(1.0, tk.END)
        self.display_text.insert(tk.END, text.strip())
        self.display_text.config(state=tk.DISABLED)

    def enable_buttons(self):
        for btn in self.buttons.values():
            btn.config(state=tk.NORMAL, bg="#007bff", fg="white")

    def disable_buttons(self):
        for btn in self.buttons.values():
            btn.config(state=tk.DISABLED, bg="#e0e0e0", fg="gray")


if __name__ == "__main__":
    root = tk.Tk()
    app = QuizClient(root)
    root.mainloop()