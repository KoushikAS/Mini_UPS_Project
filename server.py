import socket

from google.protobuf.internal.decoder import _DecodeVarint32
from google.protobuf.internal.encoder import _EncodeVarint

from proto import world_ups_pb2, amazon_ups_pb2

# WORLD_HOST = "docker.for.mac.localhost"
WORLD_HOST = "152.3.53.130"
WORLD_PORT = 12345

# UPS_HOST = "0.0.0.0"
# UPS_PORT = 34567

# AMAZON_HOST = "docker.for.mac.localhost"
AMAZON_HOST = "152.3.53.130"
AMAZON_PORT = 34567

MAX_RETRY = 10


def send_to_socket(world_socket: socket, msg):
    serialize_msg = msg.SerializeToString()
    _EncodeVarint(world_socket.send, len(serialize_msg), None)
    world_socket.send(serialize_msg)


def recv_from_socket(world_socket: socket) -> str:
    var_int_buff = []
    while True:
        buf = world_socket.recv(1)
        var_int_buff += buf
        msg_len, new_pos = _DecodeVarint32(var_int_buff, 0)
        if new_pos != 0:
            break
    return world_socket.recv(msg_len)


def create_in_world(UConnect):
    for i in range(0, MAX_RETRY):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as world_socket:
            world_socket.connect((WORLD_HOST, WORLD_PORT))
            send_to_socket(world_socket, UConnect)
            try:
                msg = recv_from_socket(world_socket)
                UConnected = world_ups_pb2.UConnected()
                UConnected.ParseFromString(msg)
                if UConnected.result == "connected!":
                    return UConnected
                else:
                    print("Failed to create the world with error message " + str(UConnected.result))
            except:
                print("World Simulator Error: Failed to create the world")

    print("Failed to create the world " + str(UConnect.worldid) + " after " + str(MAX_RETRY) + " iteration. exiting")
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


def setup_world() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as amazon_socket:
        for i in range(0, MAX_RETRY):
            try:
                amazon_socket.connect((AMAZON_HOST, AMAZON_PORT))
                world_id = create_new_world()

                # sending world id to amazon
                UtoAzConnect = amazon_ups_pb2.UtoAzConnect()
                UtoAzConnect.worldid = world_id

                send_to_socket(amazon_socket, UtoAzConnect)

                msg = recv_from_socket(amazon_socket)
                AzConnected = amazon_ups_pb2.AzConnected()
                AzConnected.ParseFromString(msg)

                if AzConnected.result == "success":
                    print("Amazon successfully joined the world")
                    return world_id
                else:
                    print("Amazon failed to join the world.")
            except:
                print("Amazon Network Error: Amazon failed to join the world.")

        print("Amazon is not able to join the world after " + str(MAX_RETRY) + " iteration. exiting")


if __name__ == "__main__":
    setup_world()

    # world_id = create_new_world()
    # add_truck(world_id, 1)
    # add_truck(world_id, 2)
    # add_truck(world_id, 1)
