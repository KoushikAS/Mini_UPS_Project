import socket
import threading
import time

from google.protobuf.internal.decoder import _DecodeVarint32
from google.protobuf.internal.encoder import _EncodeVarint

from models.base import Base, engine, Session
from models.item import Item
from models.package import Package
from models.truck import Truck, TruckStatus
from models.worldorder import WorldOrder, OrderType, OrderStatus
from proto import world_ups_pb2, amazon_ups_pb2

# WORLD_HOST = "localhost"
# WORLD_HOST = "docker.for.mac.localhost"
WORLD_HOST = "152.3.53.130"
WORLD_PORT = 12345

# AMAZON_HOST = "docker.for.mac.localhost"
AMAZON_HOST = "152.3.53.130"
AMAZON_PORT = 34567

MAX_RETRY = 10


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


def send_UCommands_request(world_socket, UCommands):
    print("Sending U command request")
    for i in range(0, MAX_RETRY):
        print("sending")
        send_to_socket(world_socket, UCommands)
        try:
            msg = recv_from_socket(world_socket)
            UResponses = world_ups_pb2.UResponses()
            UResponses.ParseFromString(msg)
            return UResponses
        except Exception as e:
            print("World Simulator Error: Failed to create the world with error " + str(e))

    print("Failed to send UCommand after " + str(MAX_RETRY) + " iteration. exiting")
    exit()


def create_in_world(world_socket, UConnect):
    for i in range(0, MAX_RETRY):
        send_to_socket(world_socket, UConnect)
        try:
            msg = recv_from_socket(world_socket)
            print(msg)
            UConnected = world_ups_pb2.UConnected()
            UConnected.ParseFromString(msg)
            if UConnected.result == "connected!":
                return UConnected
            else:
                print("Failed to create the world with error message " + str(UConnected.result))
        except Exception as e:
            print("World Simulator Error: Failed to create the world")
            print(str(e))

    print("Failed to create the world " + str(UConnect.worldid) + " after " + str(MAX_RETRY) + " iteration. exiting")
    exit()


def create_new_world(world_socket) -> int:
    print("Creating a new World")

    # creating a UConnect request with worldId = null
    UConnect = world_ups_pb2.UConnect()
    UConnect.isAmazon = False

    for i in range(0, 5):
        truck_id = add_truck()
        UInitTruck = world_ups_pb2.UInitTruck()
        UInitTruck.id = truck_id
        UInitTruck.x = 0
        UInitTruck.y = 0
        UConnect.trucks.append(UInitTruck)

    UConnected = create_in_world(world_socket, UConnect)
    print("Successfully created a new world with world_id " + str(UConnected.worldid))
    return UConnected.worldid


def add_truck() -> int:
    session = Session()
    truck = Truck()
    session.add(truck)
    session.commit()
    truck_id = truck.id
    session.close()
    print("Adding a Truck with id " + str(truck_id) + " to DB")
    return truck_id


def setup_world_with_amazon():
    for i in range(0, MAX_RETRY):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as amazon_socket:
            try:
                amazon_socket.connect((AMAZON_HOST, AMAZON_PORT))
                # sending world id to amazon
                UtoAzConnect = amazon_ups_pb2.UtoAzConnect()
                UtoAzConnect.worldid = world_id

                send_to_socket(amazon_socket, UtoAzConnect)

                msg = recv_from_socket(amazon_socket)
                AzConnected = amazon_ups_pb2.AzConnected()
                AzConnected.ParseFromString(msg)

                if AzConnected.result == "success":
                    print("Amazon successfully joined the world")
                    return
                else:
                    print("Amazon failed to join the world.")
            except Exception as e:
                print("Amazon Network Error: Amazon failed to join the world.")
                print(str(e))

    print("Amazon is not able to join the world after " + str(MAX_RETRY) + " iteration. exiting")


def prepare_UGoPickupRequest(order):
    UGoPickup = world_ups_pb2.UGoPickup()
    UGoPickup.truckid = order.truckId
    UGoPickup.whid = order.warehouseId
    UGoPickup.seqnum = order.seqNo

    return UGoPickup


def prepare_UCommandsRequest():
    session = Session()

    orders = session.query(WorldOrder) \
        .filter(WorldOrder.status == OrderStatus.ACTIVE) \
        .with_for_update()

    if orders.first() is None:
        print("No new command")
        return None

    UCommands = world_ups_pb2.UCommands()

    for order in orders:
        if order.orderType == OrderType.PICKUP:
            UCommands.pickups.append(prepare_UGoPickupRequest(order))
        else:
            pass
        order.status = OrderStatus.SENT
        session.add(order)

    session.commit()
    return UCommands


# def receive_package(world_socket, amazon_socket, world_id: int):
#     # Receive package and warehouse from Amazon
#     print("Waiting to Receive from Amazon")
#     msg = recv_from_socket(amazon_socket)
#     print("Received Amazon")
#     AMessage = amazon_ups_pb2.AMessage()
#     AMessage.ParseFromString(msg)
#
#     prepare_UGoPickup(world_socket, truck_id, AMessage.sendTruck.warehouse_id,
#                       package_id)  # send truck to warehouse
#     print("Sent Truck")
#     # send a message to Amazon saying that package has arrived.
#     UMessage = amazon_ups_pb2.UMessage()
#     UMessage.truckAtWH.truck_id = truck_id
#     UMessage.truckAtWH.package_id = package_id
#     UMessage.truckAtWH.warehouse_id = AMessage.sendTruck.warehouse_id
#
#     print("Sending Truck at WH to Amazon")
#     send_to_socket(amazon_socket, UMessage)
#     print("Sent")


if __name__ == "__main__":
    Base.metadata.create_all(engine)
    world_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    world_socket.connect((WORLD_HOST, WORLD_PORT))

    world_id = create_new_world(world_socket)
    # setup_world_with_amazon()

    while True:
        print("Starting a new cycle")
        UCommands = prepare_UCommandsRequest()

        if UCommands is not None:
            UResponses = send_UCommands_request(world_socket, UCommands)

            for error in UResponses.error:
                print(
                    "Error with message " + str(error.err) + " original sequence no " + str(
                        error.originseqnum) + " sequence no " + str(error.seqnum))

        else:
            print("No new command ")

        time.sleep(15)  # Sleep for 5 seconds
