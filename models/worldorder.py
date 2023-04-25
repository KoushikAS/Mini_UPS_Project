import enum

from sqlalchemy import Column, Integer, ForeignKey, Enum, String
from sqlalchemy.orm import relationship

from models.base import Base


class OrderType(enum.Enum):
    DELIVERY = 'delivery'
    PICKUP = 'pickup'
    QUERIES = 'query'


class OrderStatus(enum.Enum):
    NEW = 'new'
    ACKED = 'acked'
    ERROR = 'error'


class WorldOrder(Base):
    __tablename__ = 'worldorder'

    seqNo = Column(Integer, primary_key=True)
    status = Column(Enum(OrderStatus), default=OrderStatus.NEW)
    orderType = Column(Enum(OrderType), nullable=False)

    truckId = Column(Integer, ForeignKey('truck.id'))
    truck = relationship("Truck")

    warehouseId = Column(Integer)
    errorDescription = Column(String)

    def __init__(self, orderType, truckId, warehouseId):
        self.orderType = orderType
        self.truckId = truckId
        self.warehouseId = warehouseId
