import socket

HOST = "127.0.0.1"   # server address
PORT = 5000          # server port


def start_client():
    # create socket
    client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    # connect to server
    client.connect((HOST, PORT))

    # receive welcome message
    message = client.recv(1024)
    print(message.decode())

    while True:
        # take input from user
        msg = input("Enter message (type 'quit' to exit): ")

        if msg.lower() == "quit":
            break

        # send message to server
        client.send(msg.encode())

    # close connection
    client.close()


start_client()