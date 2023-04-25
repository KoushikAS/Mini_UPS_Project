import socket
import time

from proto import amazon_ups_pb2
from testing import world_amazon_pb2
from google.protobuf.internal.encoder import _EncodeVarint
from google.protobuf.internal.decoder import _DecodeVarint32
from sqlalchemy import and_, or_

HOST = "localhost"
PORT = 54321
WORLD_HOST = "localhost"
WORLD_PORT = 23456

def send_to_socket(socket: socket, msg):
    serialize_msg = msg.SerializeToString()
    _EncodeVarint(socket.send, len(serialize_msg), None)
    socket.send(serialize_msg)

def recv_from_socket(socket: socket) -> str:
    var_int_buff = []
    while True:
        buf = socket.recv(1)
        var_int_buff += buf
        msg_len, new_pos = _DecodeVarint32(var_int_buff, 0)
        if new_pos != 0:
            break
    return socket.recv(msg_len)

world_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
world_socket.connect((WORLD_HOST, WORLD_PORT))

AConnect = world_amazon_pb2.AConnect()
AConnect.worldid = 5
AConnect.isAmazon = True

AInitWarehouse = world_amazon_pb2.AInitWarehouse()
AInitWarehouse.id = 1
AInitWarehouse.x = 1
AInitWarehouse.y = 2

AConnect.initwh.append(AInitWarehouse)

send_to_socket(world_socket, AConnect)
msg = recv_from_socket(world_socket)
print(msg)


with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
    s.connect((HOST, PORT))

    AItem = amazon_ups_pb2.AItem()
    AItem.description = "abc"
    AItem.count = 2

    AMessage = amazon_ups_pb2.AMessage()
    AMessage.sendTruck.package_id = 5
    AMessage.sendTruck.warehouse_id = 1
    AMessage.sendTruck.user_id = 1
    AMessage.sendTruck.x = 1
    AMessage.sendTruck.y = 1
    AMessage.sendTruck.items.append(AItem)

    send_to_socket(s, AMessage)
    # AMessage.sendTruck.package_id = 2
    # send_to_socket(s, AMessage)
    # AMessage.sendTruck.package_id = 5
    # time.sleep((5))
    # send_to_socket(s, AMessage)

print("End")
