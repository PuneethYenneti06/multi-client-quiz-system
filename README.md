#  Multi-Client Quiz System

A multi-client online quiz platform built with **Python TCP sockets** and **SSL/TLS encryption**. The server hosts a GUI-based live spectator dashboard where an admin configures and monitors the quiz in real time, while multiple clients connect simultaneously to compete — with scores tracked, latency measured, and a live leaderboard broadcast after every round.

---

##  Table of Contents

- [Features](#features)
- [Architecture](#architecture)
- [Project Structure](#project-structure)
- [Prerequisites](#prerequisites)
- [Setup & Installation](#setup--installation)
- [SSL Certificate Generation](#ssl-certificate-generation)
- [Running the Application](#running-the-application)
- [How It Works](#how-it-works)
- [Configuration](#configuration)
- [Question Format](#question-format)
- [Performance & Latency Logging](#performance--latency-logging)
- [Technologies Used](#technologies-used)

---

##  Features

- **Multi-Client TCP Support** — Multiple players connect simultaneously; each client handled in a dedicated thread
- **SSL/TLS Encryption** — All client-server traffic is wrapped in TLS 1.2+ using a CA-signed certificate chain
- **Tkinter GUI — Server & Client** — Server has a live spectator dashboard; clients get a clean multiple-choice interface
- **Setup Wizard** — Admin configures number of questions, time limit per question, and leaderboard frequency before starting
- **Real-Time Leaderboard** — Scores are broadcast to all clients after configurable question intervals
- **Per-Question Reveal** — After each question, the correct answer is revealed with a 5-second countdown
- **Latency Tracking** — Server measures round-trip answer latency per client per question and logs fairness metrics
- **Performance Logging** — Latency stats exported to `docs/performance.json` after each question
- **Graceful Disconnect Handling** — Clients that drop mid-quiz are removed cleanly without affecting others
- **85 Built-in Questions** — Covers Python, networking, databases, OS, data structures, and more — shuffled each game

---

##  Architecture

```
┌─────────────────────────────────────────┐
│           Quiz Server (server.py)        │
│                                          │
│  ┌──────────────┐  ┌──────────────────┐ │
│  │ Setup Wizard │  │ Spectator Dash   │ │
│  │  (Tkinter)   │─►│   (Tkinter GUI)  │ │
│  └──────────────┘  └──────────────────┘ │
│                                          │
│  ┌───────────────────────────────────┐  │
│  │  quiz_loop() — background thread  │  │
│  │  Broadcasts questions, scores     │  │
│  │  Tracks answers + latency         │  │
│  └───────────────────────────────────┘  │
│                                          │
│  ┌──────────┐  ┌──────────┐             │
│  │ Thread 1 │  │ Thread 2 │  ...        │  ◄── one per client
│  └──────────┘  └──────────┘             │
└───────────────┬─────────────────────────┘
                │  SSL/TLS over TCP — Port 5000
     ┌──────────┼──────────┐
     ▼          ▼          ▼
┌─────────┐ ┌─────────┐ ┌─────────┐
│Client 1 │ │Client 2 │ │Client N │
│(Tkinter)│ │(Tkinter)│ │(Tkinter)│
└─────────┘ └─────────┘ └─────────┘
```

---

##  Project Structure

```
multi-client-quiz-system/
│
├── server/
│   └── server.py              # Quiz server — GUI dashboard, game loop, networking
│
├── client/
│   └── client.py              # Quiz client — GUI interface, SSL connection, answer submission
│
├── data/
│   └── questions.csv          # 85 multiple-choice questions (shuffled each game)
│
├── security/
│   └── certs/
│       ├── openssl.cnf        # OpenSSL config (SAN for localhost + LAN IP)
│       ├── ca.crt             # Certificate Authority cert (committed)
│       ├── ca.srl             # CA serial tracker
│       ├── server.crt         # Server certificate (committed)
│       ├── server.csr         # Certificate signing request
│       └── server.key         #  Private key — NOT committed (see .gitignore)
│
├── docs/
│   └── performance.json       # Auto-generated latency + fairness report (per question)
│
├── .gitignore
└── README.md
```

---

##  Prerequisites

- Python 3.8 or higher
- `tkinter` (included with standard Python on Windows/macOS; see below for Linux)
- `openssl` command-line tool (for generating the private key)

**Linux — install tkinter if missing:**
```bash
sudo apt-get install python3-tk
```

No third-party Python packages are required. The project uses only the standard library (`socket`, `ssl`, `threading`, `tkinter`, `csv`, `json`, `pathlib`).

---

##  Setup & Installation

**1. Clone the repository**
```bash
git clone https://github.com/PuneethYenneti06/multi-client-quiz-system.git
cd multi-client-quiz-system
```

**2. Generate the server private key** (the `.crt` and CA files are already included):
```bash
openssl genrsa -out security/certs/server.key 2048
```

> The `server.key` is excluded from version control via `.gitignore`. You must generate it once locally. The `server.crt` and `ca.crt` already present in the repo are signed and ready to use.

---

##  SSL Certificate Generation

>  **Only needed if you want to regenerate the full certificate chain from scratch** (e.g., to add a new LAN IP). The certs already in the repo work out of the box for `localhost` and `10.5.25.223`.

**Step 1 — Generate the CA key and certificate:**
```bash
openssl genrsa -out security/certs/ca.key 4096
openssl req -x509 -new -nodes -key security/certs/ca.key -sha256 -days 1825 \
  -out security/certs/ca.crt \
  -subj "/C=US/ST=State/L=City/O=QuizCA/CN=QuizRootCA"
```

**Step 2 — Generate the server key and CSR:**
```bash
openssl genrsa -out security/certs/server.key 2048
openssl req -new -key security/certs/server.key \
  -out security/certs/server.csr \
  -subj "/C=US/ST=State/L=City/O=QuizApp/CN=localhost"
```

**Step 3 — Sign the server cert with the CA:**
```bash
openssl x509 -req -in security/certs/server.csr \
  -CA security/certs/ca.crt -CAkey security/certs/ca.key \
  -CAcreateserial -out security/certs/server.crt -days 825 -sha256 \
  -extfile security/certs/openssl.cnf -extensions v3_server
```

To allow connections from a different LAN IP, edit `security/certs/openssl.cnf` and update `IP.2` before Step 3.

---

##  Running the Application

**Start the server** (run this first):
```bash
python server/server.py
```

The Setup Wizard window will appear. Configure your game settings and click **Start Quiz Now**.

**Connect a client** (open one terminal/window per player):
```bash
python client/client.py
```

To connect from another machine on the same network, edit `HOST` at the top of `client/client.py`:
```python
HOST = "192.168.x.x"   # Replace with the server machine's LAN IP
```

---

##  How It Works

1. **Server starts** and opens the Setup Wizard — set question count, time limit, and leaderboard frequency.
2. **Clients connect** over SSL/TCP on port `5000`. Each is assigned a player ID (`Player 1`, `Player 2`, etc.) and their name appears in the server's lobby counter.
3. **Admin clicks "Start Quiz Now"** — the game loop activates and the server switches to the Live Spectator Dashboard.
4. **Each question** is broadcast to all clients simultaneously with a server timestamp embedded in the message header (used for latency measurement).
5. **Clients answer** by clicking A/B/C/D. Answers are sent with the client's local timestamp in the format `ANSWER|<timestamp>|<choice>`.
6. **After the timer expires**, the server scores all answers (+10 for correct, 0 for wrong/no answer), sends each client a personalised `RESULT` message, and reveals the correct answer for 5 seconds.
7. **Leaderboard** is broadcast every N questions (configurable). The server's spectator panel updates live throughout.
8. **Latency stats** for that question are printed to the server's terminal and saved to `docs/performance.json`.
9. **Quiz ends** when all questions are done, or the admin clicks "End Quiz Early". Clients receive a `QUIZ_ENDED` message and the server reverts to the Setup Wizard for the next game.

---

##  Configuration

All configuration is done via the **Setup Wizard GUI** on the server, or by editing constants at the top of the respective files.

| Setting | Location | Default | Description |
|---|---|---|---|
| `HOST` | `server/server.py` | `0.0.0.0` | Interface the server binds to |
| `PORT` | `server/server.py` | `5000` | TCP port for all connections |
| `HOST` | `client/client.py` | `127.0.0.1` | Server IP the client connects to |
| Question count | Setup Wizard | `5` | How many questions to ask (max: all 85) |
| Time per question | Setup Wizard | `20s` | Countdown timer per question |
| Leaderboard frequency | Setup Wizard | Every `1` question | How often to broadcast the leaderboard |

---

##  Question Format

Questions are stored in `data/questions.csv`. You can add, edit, or remove rows freely.

```
Question,OptionA,OptionB,OptionC,OptionD,Correct
What does TCP stand for?,Transmission Control Protocol,Transfer Control Protocol,Transmission Communication Protocol,Transfer Communication Protocol,A
Which data structure uses LIFO?,Queue,Tree,Graph,Stack,D
```

- `Correct` must be one of `A`, `B`, `C`, or `D` (case-insensitive)
- Questions are **shuffled randomly** at server startup each game
- The first row must be the header row exactly as shown above

---

##  Performance & Latency Logging

After every question, the server computes and prints latency statistics per player to the terminal:

```
--- Latency Stats for Question 3 ---
Player 1: Avg=12.45ms, Max=18.20ms, Min=9.10ms (Samples=3)
Player 2: Avg=31.80ms, Max=45.60ms, Min=22.30ms (Samples=3)

--- Fairness Evaluation ---
Fairness gap: 19.35 ms
Average latency: 22.13 ms
Normalized variation: 0.8746
---------------------------
```

This data is also saved to `docs/performance.json`:

```json
{
    "clients": {
        "Player 1": {
            "avg_latency_ms": 12.45,
            "max_latency_ms": 18.20,
            "min_latency_ms": 9.10,
            "samples": 3
        }
    },
    "fairness": {
        "fairness_gap": 19.35,
        "average_latency": 22.13,
        "normalized_variation": 0.8746
    }
}
```

The **fairness gap** measures the difference between the highest and lowest average client latencies — a lower value means a more level playing field.

---

##  Technologies Used

| Technology | Purpose |
|---|---|
| Python `socket` | TCP client-server communication |
| Python `ssl` | TLS 1.2+ encryption wrapping TCP sockets |
| Python `threading` | Concurrent client handling + background game loop |
| Python `tkinter` | GUI for both server dashboard and client interface |
| OpenSSL | Certificate Authority + server certificate generation |
| CSV | Question bank storage |
| JSON | Latency and fairness performance logging |
