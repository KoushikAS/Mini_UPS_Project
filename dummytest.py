import socket

from proto import amazon_ups_pb2
from google.protobuf.internal.encoder import _EncodeVarint

HOST = "localhost"
PORT = 54321

def send_to_socket(socket: socket, msg):
    serialize_msg = msg.SerializeToString()
    _EncodeVarint(socket.send, len(serialize_msg), None)
    socket.send(serialize_msg)

with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
    s.connect((HOST, PORT))
    AMessage = amazon_ups_pb2.AMessage()
    AMessage.sendTruck.package_id = 1
    AMessage.sendTruck.warehouse_id = 1
    AMessage.sendTruck.user_id = 1
    AMessage.sendTruck.x = 1
    AMessage.sendTruck.y = 1

    send_to_socket(s, AMessage)

print("End")