import socket
import time

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

    AItem = amazon_ups_pb2.AItem()
    AItem.description = "abc"
    AItem.count = 2


    AMessage = amazon_ups_pb2.AMessage()
    AMessage.sendTruck.package_id = 100
    AMessage.sendTruck.warehouse_id = 1
    AMessage.sendTruck.user_id = 1
    AMessage.sendTruck.x = 1
    AMessage.sendTruck.y = 1
    AMessage.sendTruck.items.append(AItem)

    send_to_socket(s, AMessage)
    AMessage.sendTruck.package_id = 11
    send_to_socket(s, AMessage)
    AMessage.sendTruck.package_id = 12
    time.sleep((5))
    send_to_socket(s, AMessage)

print("End")