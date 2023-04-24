import threading
import socket
import time

from google.protobuf.internal.decoder import _DecodeVarint32

from models.base import Base, engine, Session
from models.item import Item
from models.package import Package, PackageStatus
from models.truck import Truck, TruckStatus
from models.worldorder import WorldOrder, OrderType
from proto import amazon_ups_pb2
from sqlalchemy import and_, or_

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


def get_truck_for_package(session) -> int:
    print("Searching for Truck")
    truck = session.query(Truck) \
        .filter(Truck.status == TruckStatus.IDLE) \
        .with_for_update() \
        .first()

    print("Truck from database")
    print(truck)
    if truck:
        print("Using the Truck with Id" + str(truck.id))
        truck.status = TruckStatus.OCCUPIED
        truck_id = truck.id
    else:
        # TODO: handle if all trucks are occupied
        # print("Getting new Truck")
        # truck_id = add_truck(world_id)
        print("Did not find any Truck which is idle")
        truck_id = None
        pass

    return truck_id


def create_package(session, truck_id: int, ASendTruck, pacakge_status):

    if not ASendTruck.HasField("user_id"):
        ASendTruck.user_id = None

    package = Package(ASendTruck.package_id, truck_id, ASendTruck.warehouse_id, ASendTruck.user_id, ASendTruck.x,
                          ASendTruck.y, pacakge_status)
    session.add(package)

    for item in ASendTruck.items:
        i = Item(ASendTruck.package_id, item.description, item.count)
        session.add(i)

    return ASendTruck.package_id


def submitOrder(session, order_type, truck_id):
    order = WorldOrder(order_type, truck_id)
    session.add(order)
    seq_no = order.seqNo
    print("Added order with a seqno " + str(seq_no) + " to DB")

def handle_ASendTruck(ASendTruck):
    order_type = OrderType.PICKUP

    session = Session()
    existing_package = session.query(Package) \
        .filter(Package.userId == ASendTruck.user_id, or_(Package.status == PackageStatus.CREATED, Package.status == PackageStatus.WAREHOUSE)) \
        .with_for_update() \
        .first()
    print("Existing Package")
    print(existing_package)

    if existing_package is None:
        # Check if package can be clubbed to previous trucks and exit
        truck_id = get_truck_for_package(session)  # If not get a truck id
        print("Got a new Truck")
        # create Package
        create_package(session, truck_id, ASendTruck, PackageStatus.CREATED)
        print("created a Package")
    else:
        truck_id = existing_package.truckId
        print("Getting an existing Truck")
        # create Package
        create_package(session, truck_id, ASendTruck, PackageStatus.WAREHOUSE)
        print("created a Package")

    submitOrder(session, order_type, truck_id)

    session.commit()


def handle_ATruckLoaded(ATruckLoaded):

    order_type = OrderType.DELIVERY
    truck_id = ATruckLoaded.truck_id

    session = Session()
    package = session.query(Package) \
        .filter(Package.packageId == ATruckLoaded.package_id)\
        .with_for_update() \
        .scalar()
    package.status = PackageStatus.LOADED
    session.commit()

    other_packages = session.query(Package) \
        .filter(Package.userId == package.package, Package.status == PackageStatus.LOADING)\
        .with_for_update() \
        .scalar()\
        .first()

    if other_packages is None:  #Only submit order if all packages of are loaded in the truck.
        submitOrder(session, order_type, truck_id)

    session.commit()



def handle_connection(AMessage):
    print("here")
    if AMessage.HasField('sendTruck'):
        handle_ASendTruck(AMessage.sendTruck)
    elif AMessage.HasField('truckLoaded'):
        handle_ATruckLoaded(AMessage.truckLoaded)
    else:
        print("Wrong A Message")
        return




if __name__ == "__main__":
    # Base.metadata.create_all(engine)

    # To hold onto all the threads spawned to check if they have been closed
    threads = []

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind((UPS_HOST, UPS_PORT))
        s.listen()
        conn, addr = s.accept()
        # # Waiting tmp
        # print("Waiting for Az connect request")
        # msg = recv_from_socket(conn)
        # print("Received from Az connect request")
        # AzConnected = amazon_ups_pb2.AzConnected()
        # AzConnected.ParseFromString(msg)
        #
        # if AzConnected.result == "success":
        #     print("Amazon successfully joined the world")
        # else:
        #     print("Amazon failed to join the world.")
        #     exit()

        while True:
            print("waiting")
            try:
                msg = recv_from_socket(conn)
                print("Received a connection")
                print(msg)
                AMessage = amazon_ups_pb2.AMessage()
                AMessage.ParseFromString(msg)
                # Create a new thread to handle the connection
                t = threading.Thread(target=handle_connection, args=(AMessage,))
                threads.append(t)
                t.start()
            except Exception as e:
                print("Error with " + str(e))
                print("Socket closed")
                break

    # Waiting for all the threads to complete
    for thread in threads:
        thread.join()

    print("End")
