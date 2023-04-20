import socket
import threading

from google.protobuf.internal.decoder import _DecodeVarint32
from google.protobuf.internal.encoder import _EncodeVarint

from models.base import Base, engine, Session
from models.item import Item
from models.package import Package
from models.truck import Truck, TruckStatus
from models.worldorder import WorldOrder, OrderType
from proto import world_ups_pb2, amazon_ups_pb2

# WORLD_HOST = "localhost"
WORLD_HOST = "docker.for.mac.localhost"
# WORLD_HOST = "152.3.53.130"
WORLD_PORT = 12345

UPS_HOST = "0.0.0.0"
UPS_PORT = 34567

AMAZON_HOST = "docker.for.mac.localhost"
# AMAZON_HOST = "152.3.53.130"
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


def send_UConnect_request(world_socket, UConnect):
    if world_socket is None:
        world_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        world_socket.connect((WORLD_HOST, WORLD_PORT))

    for i in range(0, MAX_RETRY):
        send_to_socket(world_socket, UConnect)
        try:
            msg = recv_from_socket(world_socket)
            print("Here")
            print(msg)
            UConnected = world_ups_pb2.UConnected()
            UConnected.ParseFromString(msg)
            if UConnected.result == "connected!":
                return world_socket, UConnected
            else:
                print("Failed to create the world with error message " + str(UConnected.result))
        except Exception as e:
            print("World Simulator Error: Failed to create the world with error " + str(e))

    print("Failed to create the world " + str(UConnect.worldid) + " after " + str(MAX_RETRY) + " iteration. exiting")
    exit()


def send_UCommands_request(world_socket, UCommands):
    print("Sending U command request")
    for i in range(0, MAX_RETRY):
        world_socket.connect((WORLD_HOST, WORLD_PORT))
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


def create_new_world() :
    print("Creating a new World")

    # creating a UConnect request with worldId = null
    UConnect = world_ups_pb2.UConnect()
    UConnect.isAmazon = False

    world_socket, UConnected = send_UConnect_request(None, UConnect)
    print("Successfully created a new world with world_id " + str(UConnected.worldid))
    return world_socket, UConnected.worldid


def add_truck(world_socket, world_id: int) -> int:
    session = Session()
    truck = Truck()
    truck.world_id = world_id
    session.add(truck)
    session.commit()
    truck_id = truck.id
    session.close()
    print("Adding a Truck with id " + str(truck_id))
    # creating a new truck
    UInitTruck = world_ups_pb2.UInitTruck()
    UInitTruck.id = truck.id
    UInitTruck.x = 0
    UInitTruck.y = 0

    # creating a UConnect request with truck
    UConnect = world_ups_pb2.UConnect()
    UConnect.worldid = world_id
    UConnect.isAmazon = False
    UConnect.trucks.append(UInitTruck)

    send_UConnect_request(None, UConnect)
    print("Successfully created truck with truck_id " + str(truck_id))
    return truck.id


def setup_world() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as amazon_socket:
        for i in range(0, MAX_RETRY):
            try:
                amazon_socket.connect((AMAZON_HOST, AMAZON_PORT))
                world_socket, world_id = create_new_world()

                # sending world id to amazon
                UtoAzConnect = amazon_ups_pb2.UtoAzConnect()
                UtoAzConnect.worldid = world_id

                send_to_socket(amazon_socket, UtoAzConnect)

                msg = recv_from_socket(amazon_socket)
                AzConnected = amazon_ups_pb2.AzConnected()
                AzConnected.ParseFromString(msg)

                if AzConnected.result == "success":
                    print("Amazon successfully joined the world")

                    # tmp
                    receive_order(world_socket, amazon_socket, world_id)

                    return world_id
                else:
                    print("Amazon failed to join the world.")
            except Exception as e:
                print("Amazon Network Error: Amazon failed to join the world.")
                print(str(e))

        print("Amazon is not able to join the world after " + str(MAX_RETRY) + " iteration. exiting")


def get_truck_for_package(world_socket, world_id: int) -> int:
    print("Searching for Truck")
    session = Session()
    truck = session.query(Truck) \
        .filter(Truck.status == TruckStatus.IDLE, world_id == world_id) \
        .with_for_update() \
        .first()

    if truck:
        print("Using the Truck with Id" + str(truck.id))
        truck.status = TruckStatus.TRAVELING
        truck_id = truck.id
    else:
        print("Getting new Truck")
        truck_id = add_truck(world_socket, world_id)
    session.commit()
    session.close()

    return truck_id


def send_truck_to_warehouse(world_socket, truck_id: int, warehouse_id: int, package_id: int):
    print("sending truck " + str(truck_id) + " to warehouse " + str(warehouse_id) + " to receive package " + str(
        package_id))
    session = Session()
    order = WorldOrder(OrderType.DELIVERY, truck_id, package_id, warehouse_id)
    session.add(order)
    session.commit()
    seq_no = order.seqNo
    session.close()

    # Instructing Truck to go to the warehouse
    UGoPickup = world_ups_pb2.UGoPickup()
    UGoPickup.truckid = truck_id
    UGoPickup.whid = warehouse_id
    UGoPickup.seqnum = seq_no

    UCommands = world_ups_pb2.UCommands()
    UCommands.pickups.append(UGoPickup)
    UResponses = send_UCommands_request(world_socket, UCommands)

    for error in UResponses.error:
        print(
            "Error with message " + error.err + " original sequence no " + error.originseqnum + " sequence no " + error.seqnum)


def create_package(truck_id: int, ASendTruck):
    session = Session()

    if not ASendTruck.HasField("user_id"):
        ASendTruck.user_id = -1

    package = Package(ASendTruck.package_id, truck_id, ASendTruck.warehouse_id, ASendTruck.user_id, ASendTruck.x,
                      ASendTruck.y)
    session.add(package)
    session.commit()

    for item in ASendTruck.items:
        i = Item(ASendTruck.package_id, item.description, item.count)
        session.add(i)
        session.commit()

    session.close()

    return ASendTruck.package_id


def receive_order(world_socket, amazon_socket, world_id: int):
    # Receive package and warehouse from Amazon
    # print("Waiting to Receive from Amazon")
    # msg = recv_from_socket(socket)
    # print("Received Amazon")
    # AMessage = amazon_ups_pb2.AMessage()
    # AMessage.ParseFromString(msg)

    ASendTruck = amazon_ups_pb2.ASendTruck()
    ASendTruck.package_id = 1
    ASendTruck.warehouse_id = 1
    ASendTruck.x = 1
    ASendTruck.y = 1

    AMessage = amazon_ups_pb2.AMessage()
    AMessage.sendTruck.package_id = 1
    AMessage.sendTruck.warehouse_id = 1
    AMessage.sendTruck.x = 1
    AMessage.sendTruck.y = 1

    # Check if package can be clubbed to previous trucks and exit
    truck_id = get_truck_for_package(world_socket, world_id)  # If not get a truck id
    print("Got Truck")

    # Create package
    package_id = create_package(truck_id, AMessage.sendTruck)
    print("Package Recevied")

    send_truck_to_warehouse(truck_id, AMessage.sendTruck.warehouse_id, package_id)  # send truck to warehouse
    print("Sent Truck")
    # send a message to Amazon saying that package has arrived.
    UMessage = amazon_ups_pb2.UMessage()
    UTruckAtWH = amazon_ups_pb2.UTruckAtWH()
    UTruckAtWH.truck_id = truck_id
    UTruckAtWH.package_id = package_id
    UTruckAtWH.warehouse_id = AMessage.sendTruck.warehouse_id

    UMessage.truckAtWH = UTruckAtWH
    print("Sending Truck at WH to Amazon")
    send_to_socket(amazon_socket, UMessage)
    print("Sent")


def handle_connection(socket, world_id: int):
    print("here")
    with socket:
        print("hey")
        receive_order(socket, world_id)


if __name__ == "__main__":
    Base.metadata.create_all(engine)
    world_id = setup_world()

    # world_socket, world_id = create_new_world()
    # receive_order(world_socket, None, world_id)

    '''
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind((UPS_HOST, UPS_PORT))
        s.listen()
        while True:
            conn, addr = s.accept()
            print("Received a connection")
            # Create a new thread to handle the connection
            t = threading.Thread(target=handle_connection, args=(conn, world_id))
            t.start()
    '''
    # Base.metadata.create_all(engine)
    # session = Session()
    # for i in range(10):
    #     truck = Truck()
    #     session.add(truck)
    #     session.commit()
    #     print(truck.id)
    # print("Added Truck")

    # for i in range(0,100):
    #     add_truck(world_id, i)
    # add_truck(world_id, 1)
    # add_truck(world_id, 2)
    # add_truck(world_id, 1)
