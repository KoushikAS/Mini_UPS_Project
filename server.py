import socket

from google.protobuf.internal.decoder import _DecodeVarint32
from google.protobuf.internal.encoder import _EncodeVarint

from proto import world_ups_pb2

WORLD_HOST = "docker.for.mac.localhost"
WORLD_PORT = 12345


def send_to_world(world_socket: socket, msg):
    serialize_msg = msg.SerializeToString()
    _EncodeVarint(world_socket.send, len(serialize_msg), None)
    world_socket.send(serialize_msg)


def recv_from_world(world_socket: socket) -> str:
    var_int_buff = []
    while True:
        buf = world_socket.recv(1)
        var_int_buff += buf
        msg_len, new_pos = _DecodeVarint32(var_int_buff, 0)
        if new_pos != 0:
            break
    return world_socket.recv(msg_len)


def create_in_world(UConnect):
    for i in range(0, 10):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as world_socket:
            world_socket.connect((WORLD_HOST, WORLD_PORT))
            send_to_world(world_socket, UConnect)
            try:
                msg = recv_from_world(world_socket)
                UConnected = world_ups_pb2.UConnected()
                UConnected.ParseFromString(msg)
                if UConnected.result == "connected!":
                    return UConnected
                else:
                    print("Failed to create the world with error message " + str(UConnected.result))
            except:
                print("World Simulator Error: Failed to create the world")

    print("Failed to create the world " + str(UConnect.worldid) + " after 10 iteration")
    exit()


def create_new_world() -> int:
    print("Creating a new World")

    # creating a UConnect request with worldId = null
    UConnect = world_ups_pb2.UConnect()
    UConnect.isAmazon = False

    UConnected = create_in_world(UConnect)
    print("Successfully created a new world with world_id " + str(UConnected.worldid))
    return UConnected.worldid


def add_truck(world_id: int, truck_id: int):
    print("Adding a Truck with id " + str(truck_id))
    # creating a new truck
    UInitTruck = world_ups_pb2.UInitTruck()
    UInitTruck.id = truck_id
    UInitTruck.x = 0
    UInitTruck.y = 0

    # creating a UConnect request with truck
    UConnect = world_ups_pb2.UConnect()
    UConnect.worldid = world_id
    UConnect.isAmazon = False
    UConnect.trucks.append(UInitTruck)

    create_in_world(UConnect)
    print("Successfully created truck with truck_id " + str(truck_id))


if __name__ == "__main__":
    world_id = create_new_world()
    add_truck(world_id, 1)
    add_truck(world_id, 2)
    # add_truck(world_id, 1)
