import enum

from sqlalchemy import Column, Integer, ForeignKey, Enum
from sqlalchemy.orm import relationship

from models.base import Base


class OrderType(enum.Enum):
    DELIVERY = 'delivery'
    PICKUP = 'pickup'
    QUERIES = 'query'


class OrderStatus(enum.Enum):
    ACTIVE = 'active'
    COMPLETE = 'complete'


class WorldOrder(Base):
    __tablename__ = 'worldorder'

    seqNo = Column(Integer, primary_key=True)
    status = Column(Enum(OrderStatus), default=OrderStatus.ACTIVE)
    orderType = Column(Enum(OrderType), nullable=False)

    truckId = Column(Integer, ForeignKey('truck.id'))
    truck = relationship("Truck")

    packageId = Column(Integer, ForeignKey('package.packageId'))
    package = relationship("Package")

    warehouseId = Column(Integer)

    def __init__(self, orderType, truckId, packageId, warehouseId):
        self.orderType = orderType
        self.truckId = truckId
        self.packageId = packageId
        self.warehouseId = warehouseId
