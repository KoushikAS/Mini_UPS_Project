import select
import socket
import time

from google.protobuf.internal.decoder import _DecodeVarint32
from google.protobuf.internal.encoder import _EncodeVarint

from models.base import Base, engine, Session
from models.package import Package, PackageStatus
from models.truck import Truck, TruckStatus
from models.users import Users
from models.worldorder import WorldOrder, OrderType, OrderStatus
from proto import world_ups_pb2, amazon_ups_pb2

# WORLD_HOST = "localhost"
# WORLD_HOST = "docker.for.mac.localhost"
WORLD_HOST = "152.3.53.130"
WORLD_PORT = 12345

# AMAZON_HOST = "docker.for.mac.localhost"
AMAZON_HOST = "152.3.53.130"
AMAZON_PORT = 6543

TIMEOUT = 5.0  # 5 second

MAX_RETRY = 10
from sqlalchemy import and_, or_


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


def receive_UResponse(world_socket):
    read_sockets, write_sockets, error_sockets = select.select([world_socket], [], [], TIMEOUT)

    if world_socket not in read_sockets:
        print("No message received from the socket")
        return

    try:
        msg = recv_from_socket(world_socket)
        UResponses = world_ups_pb2.UResponses()
        UResponses.ParseFromString(msg)
        return UResponses
    except Exception as e:
        print("World Simulator Error: Failed to create the world with error " + str(e))
        return None


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
                time.sleep(10)  # Sleep for 10 seconds

    print("Amazon is not able to join the world after " + str(MAX_RETRY) + " iteration. exiting")


def prepare_UGoPickupRequest(order):
    session = Session()
    package = session.query(Package) \
        .filter(Package.packageId == order.packageId) \
        .with_for_update() \
        .scalar()
    package.status = PackageStatus.WAREHOUSE
    session.commit()

    UGoPickup = world_ups_pb2.UGoPickup()
    UGoPickup.truckid = order.truckId
    UGoPickup.whid = order.warehouseId
    UGoPickup.seqnum = order.seqNo

    return UGoPickup


def prepare_UGoDeliver(order):
    session = Session()
    package = session.query(Package) \
        .filter(Package.packageId == order.packageId) \
        .with_for_update() \
        .scalar()
    package.status = PackageStatus.DELIVERY
    session.commit()

    UDeliveryLocation = world_ups_pb2.UDeliveryLocation()

    UDeliveryLocation.packageid = order.packageId
    UDeliveryLocation.x = package.x
    UDeliveryLocation.y = package.y

    UGoDeliver = world_ups_pb2.UGoDeliver()
    UGoDeliver.truckid = order.truckId
    UGoDeliver.packages.append(UDeliveryLocation)
    UGoDeliver.seqnum = order.seqNo

    truck = session.query(Truck) \
        .filter(Truck.id == order.truckId) \
        .with_for_update() \
        .scalar()

    truck.status = TruckStatus.DELIVERING
    session.commit()

    return UGoDeliver


def prepare_UCommandsRequest(acks):
    session = Session()

    orders = session.query(WorldOrder) \
        .filter(WorldOrder.status == OrderStatus.ACTIVE)

    if orders.first() is None and len(acks) == 0:
        print("No new command")
        session.close()
        return None

    UCommands = world_ups_pb2.UCommands()

    for order in orders:
        if order.orderType == OrderType.PICKUP:
            UCommands.pickups.append(prepare_UGoPickupRequest(order))
        elif order.orderType == OrderType.DELIVERY:
            UCommands.deliveries.append(prepare_UGoDeliver(order))
        else:
            pass

    for ack in acks:
        UCommands.acks.append(ack)

    session.close()
    return UCommands


def call_TruckAtWH(order):
    # send a message to Amazon saying that Truck has arrived.

    UMessage = amazon_ups_pb2.UMessage()
    UMessage.truckAtWH.truck_id = order.truck_id
    UMessage.truckAtWH.package_id = order.package_id
    UMessage.truckAtWH.warehouse_id = order.warehouse_id

    print("Send the Truck at Warehouse to Amazon")
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as amazon_socket:
        amazon_socket.connect((AMAZON_HOST, AMAZON_PORT))
        send_to_socket(amazon_socket, UMessage)
    print("Sent to Amazon")


def handle_UFinished(UFinished):
    print("U finished msg response ")
    print(UFinished)

    if UFinished.status == "arrive warehouse":
        session = Session()

        orders = session.query(WorldOrder) \
            .filter(and_(WorldOrder.orderType == OrderType.PICKUP, and_(WorldOrder.truckId == UFinished.truckid,
                                                                        or_(WorldOrder.status == OrderStatus.ACTIVE,
                                                                            WorldOrder.status == OrderStatus.SENT)))) \
            .with_for_update()

        for order in orders:
            call_TruckAtWH(order)
            order.status = WorldOrder.COMPLETE

            package = session.query(Package) \
                .filter(Package.packageId == order.packageId) \
                .with_for_update() \
                .scalar()

            package.status = PackageStatus.LOADING

        session.commit()

        truck = session.query(Truck) \
            .filter(Truck.id == UFinished.truckid) \
            .with_for_update() \
            .scalar()

        truck.status = TruckStatus.WAREHOUSE
        session.commit()
    elif UFinished.status == "arrive warehouse":
        pass
    else:
        pass


def handle_Ack(ack):
    session = Session()

    order = session.query(WorldOrder) \
        .filter(WorldOrder.seqNo == ack) \
        .with_for_update() \
        .scalar()

    # Only marking it as Sent if it is Active and not if it is already complete
    if order.status == OrderStatus.ACTIVE:
        order.status = OrderStatus.SENT

    session.commit()


def handle_UErr(UErr):
    session = Session()

    order = session.query(WorldOrder) \
        .filter(WorldOrder.seqNo == UErr.originseqnum) \
        .with_for_update() \
        .scalar()

    order.status = OrderStatus.ERROR
    order.errorDescription = UErr.err
    session.commit()


if __name__ == "__main__":
    Base.metadata.create_all(engine)

    world_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    world_socket.connect((WORLD_HOST, WORLD_PORT))

    world_id = create_new_world(world_socket)
    # setup_world_with_amazon()

    messages_to_be_acked = []

    while True:
        print("Starting a new cycle")
        UCommands = prepare_UCommandsRequest(messages_to_be_acked)

        if UCommands is not None:
            print("Sending U Command request")
            send_to_socket(world_socket, UCommands)
            messages_to_be_acked.clear()
        else:
            print("No new command ")

        UResponses = receive_UResponse(world_socket)

        if UResponses is not None:

            for ack in UResponses.acks:
                handle_Ack(ack)

            for completion in UResponses.completions:
                handle_UFinished(completion)
                messages_to_be_acked.append(completion.seqnum)

            for error in UResponses.error:
                handle_UErr(error)
                messages_to_be_acked.append(error.seqnum)
                print(
                    "Error with message " + str(error.err) + " original sequence no " + str(
                        error.originseqnum) + " sequence no " + str(error.seqnum))

        time.sleep(10)  # Sleep for 5 seconds
