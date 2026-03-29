import socket
import ssl
import threading
import tkinter as tk
from pathlib import Path

HOST = "10.5.25.223"
PORT = 5000

SECURITY_DIR = Path(__file__).resolve().parents[1] / "security"
CA_FILE = SECURITY_DIR / "certs" / "ca.crt"


class QuizClient:
    def __init__(self, root):
        self.root = root
        self.root.title("Secure Quiz Client")
        self.root.geometry("600x450")
        self.root.configure(bg="#ffffff")  # Light theme background

        # --- GUI Elements ---
        self.header = tk.Label(root, text="Secure TLS Quiz", bg="#ffffff", font=("Helvetica", 18, "bold"))
        self.header.pack(pady=15)

        # Main text area for questions and leaderboard
        self.display_text = tk.Text(root, height=10, width=60, font=("Helvetica", 12), bg="#f9f9f9", state=tk.DISABLED, wrap=tk.WORD)
        self.display_text.pack(pady=10)

        # Label to flash correct answers and statuses
        self.feedback_label = tk.Label(root, text="Waiting for connection...", bg="#ffffff", font=("Helvetica", 14, "bold"), fg="gray")
        self.feedback_label.pack(pady=10)

        # Frame for the multiple choice buttons
        self.btn_frame = tk.Frame(root, bg="#ffffff")
        self.btn_frame.pack(pady=10)

        self.buttons = {}
        for opt in ['A', 'B', 'C', 'D']:
            btn = tk.Button(self.btn_frame, text=f"Option {opt}", font=("Helvetica", 12, "bold"), width=10,
                            command=lambda o=opt: self.send_answer(o), state=tk.DISABLED, bg="#e0e0e0")
            btn.pack(side=tk.LEFT, padx=10)
            self.buttons[opt] = btn

        # --- Networking Setup ---
        self.client_socket = None
        self.connect_to_server()

    def connect_to_server(self):
        try:
            raw_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            context = ssl.create_default_context()
            context.check_hostname = False
            context.verify_mode = ssl.CERT_NONE

            self.client_socket = context.wrap_socket(raw_socket, server_hostname=HOST)
            self.client_socket.connect((HOST, PORT))

            self.update_display(f"Connected securely!\nCipher: {self.client_socket.cipher()[0]}")
            self.feedback_label.config(text="Waiting for quiz to start...", fg="blue")

            # Start background thread to listen to the server
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
                # Safely push the message update to the main GUI thread
                self.root.after(0, self.process_message, message)
            except:
                self.root.after(0, self.update_display, "Disconnected from server.")
                break

    def process_message(self, message):
        """Parses the tags sent by the server to update the GUI accordingly."""
        if "QUESTION:" in message:
            self.update_display(message)
            self.feedback_label.config(text="Select your answer!", fg="black")
            self.enable_buttons()
            
        elif "CORRECT_ANSWER:" in message:
            # Extract just the answer string
            ans = message.split("CORRECT_ANSWER:")[1].strip()
            self.feedback_label.config(text=f"Time's up! Correct Answer: {ans}", fg="#28a745") # Green text
            self.disable_buttons()
            
        elif "LEADERBOARD" in message:
            self.update_display(message)
            self.disable_buttons()
            
        else:
            self.update_display(message)

    def send_answer(self, choice):
        if self.client_socket:
            try:
                self.client_socket.send(choice.encode())
                self.feedback_label.config(text=f"Answer locked in: {choice}", fg="blue")
                self.disable_buttons() # Prevent spamming answers
            except Exception as e:
                self.update_display(f"Error sending answer: {e}")

    def update_display(self, text):
        """Helper to safely overwrite the main text box."""
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