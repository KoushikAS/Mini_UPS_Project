import socket

HOST = "localhost"
PORT = 34567

with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
    s.connect((HOST, PORT))

print("End")