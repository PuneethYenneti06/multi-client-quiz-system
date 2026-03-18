# 🔐 Multi-Client Secure Quiz System

A secure, multi-client quiz platform built using low-level socket programming with TLS encryption. The system allows multiple clients to connect to a central server, receive quiz questions in real time, submit answers, and view a live leaderboard.

---

## 🚀 Features

* Multi-client TCP server using sockets
* Concurrent client handling using threads
* TLS/SSL encrypted communication
* Quiz questions loaded from CSV file
* Real-time question broadcasting
* Timed quiz rounds
* Automatic answer evaluation
* Dynamic leaderboard updates

---

## 🧠 System Architecture

The system follows a **client-server architecture**:

* The **server** manages:

  * client connections
  * quiz questions
  * scoring
  * leaderboard

* The **clients**:

  * connect securely via TLS
  * receive quiz questions
  * submit answers

---

## 📂 Project Structure

```
multi-client-quiz-system
│
├── server/
│   └── server.py
│
├── client/
│   └── client.py
│
├── data/
│   └── questions.csv
│
├── security/
│   └── certs/
│       ├── server.crt
│       ├── ca.crt
│       └── server.key   (not included in repo)
│
├── docs/
│
├── .gitignore
└── README.md
```

---

## 🔒 Security (TLS/SSL)

* TLS encryption is implemented using Python’s `ssl` module
* The server uses a certificate (`server.crt`) and private key (`server.key`)
* Communication between client and server is fully encrypted
* Private keys are **not stored in the repository** for security reasons

---

## ⚙️ Setup Instructions

### 1️⃣ Clone the Repository

```
git clone https://github.com/your-username/multi-client-quiz-system.git
cd multi-client-quiz-system
```

---

### 2️⃣ Generate SSL Certificates (Server Only)

Run:

```
openssl req -new -x509 -days 365 -nodes \
-out security/certs/server.crt \
-keyout security/certs/server.key
```

---

### 3️⃣ Run the Server

```
python server/server.py
```

---

### 4️⃣ Run the Client

```
python client/client.py
```

Enter the **server IP address** when prompted.

---

## 🌐 Running Across Multiple PCs

1. Ensure all devices are on the same network
2. Find server IP using:

```
ipconfig
```

3. Enter this IP in the client

Example:

```
10.5.25.223
```

---

## 🎮 How It Works

1. Clients connect to the server securely using TLS
2. Server broadcasts a quiz question
3. Clients submit answers (A/B/C/D)
4. Server evaluates answers after a time limit
5. Leaderboard is updated and broadcast

---

## 🧪 Example Output

```
QUESTION:

Which data structure is immutable?

A) List
B) Dictionary
C) Set
D) Tuple
```

Client input:

```
D
```

Leaderboard:

```
LEADERBOARD
Player1: 10
Player2: 0
```

---

## 📊 Technologies Used

* Python
* Socket Programming (TCP)
* Threading
* SSL/TLS Encryption
* CSV File Handling

---

## 📌 Future Improvements

* Player usernames
* GUI interface
* Real-time leaderboard updates
* Database integration
* Timer per question

---

## 👨‍💻 Team Members

* Puneeth Yenneti
* Inchara K Kuppal
* Pramiti Udupa

---

## 📄 License

This project is developed for academic purposes.
