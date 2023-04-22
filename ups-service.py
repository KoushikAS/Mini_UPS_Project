import threading
import socket

from google.protobuf.internal.decoder import _DecodeVarint32

from models.base import Base, engine, Session
from models.item import Item
from models.package import Package, PackageStatus
from models.truck import Truck, TruckStatus
from models.worldorder import WorldOrder, OrderType
from proto import amazon_ups_pb2

UPS_HOST = "0.0.0.0"
UPS_PORT = 54321


def recv_from_socket(socket: socket) -> str:
    var_int_buff = []
    while True:
        buf = socket.recv(1)
        var_int_buff += buf
        msg_len, new_pos = _DecodeVarint32(var_int_buff, 0)
        if new_pos != 0:
            break
    return socket.recv(msg_len)


def get_truck_for_package() -> int:
    print("Searching for Truck")
    session = Session()
    truck = session.query(Truck) \
        .filter(Truck.status == TruckStatus.IDLE) \
        .with_for_update() \
        .first()

    print("Truck from database")
    print(truck)
    if truck:
        print("Using the Truck with Id" + str(truck.id))
        truck.status = TruckStatus.TRAVELING
        truck_id = truck.id
    else:
        # TODO: handle if all trucks are occupied
        # print("Getting new Truck")
        # truck_id = add_truck(world_id)
        print("Did not find any Truck which is idle")
        truck_id = None
        pass
    session.commit()
    session.close()

    return truck_id


def create_package(truck_id: int, ASendTruck):
    session = Session()

    if not ASendTruck.HasField("user_id"):
        ASendTruck.user_id = None

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


def handle_connection(conn):
    print("here")
    with conn:
        msg = recv_from_socket(conn)
        print(msg)
        AMessage = amazon_ups_pb2.AMessage()
        AMessage.ParseFromString(msg)

        if AMessage.HasField('sendTruck'):
            order_type = OrderType.PICKUP
            warehouse_id = AMessage.sendTruck.warehouse_id
            package_id = AMessage.sendTruck.package_id

            # Check if package can be clubbed to previous trucks and exit
            truck_id = get_truck_for_package()  # If not get a truck id
            print("Got Truck")

            # create Package
            create_package(truck_id, AMessage.sendTruck)
            print("created Package")

        elif AMessage.HasField('truckLoaded'):
            order_type = OrderType.DELIVERY
            truck_id = AMessage.truckLoaded.truck_id
            warehouse_id = AMessage.truckLoaded.warehouse_id
            package_id = AMessage.truckLoaded.package_id
        else:
            print("Wrong A Message")
            return

        session = Session()
        order = WorldOrder(order_type, truck_id, package_id, warehouse_id)
        session.add(order)
        session.commit()

        seq_no = order.seqNo
        print("Added order with a seqno " + str(seq_no) + " to DB")
        session.close()


if __name__ == "__main__":
    # Base.metadata.create_all(engine)

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind((UPS_HOST, UPS_PORT))
        s.listen()
        while True:
            print("waiting")
            conn, addr = s.accept()
            print("Received a connection")
            # Create a new thread to handle the connection
            t = threading.Thread(target=handle_connection, args=(conn,))
            t.start()
