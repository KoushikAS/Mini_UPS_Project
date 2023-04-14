import enum

from sqlalchemy import Column, Integer, ForeignKey, Enum
from sqlalchemy.orm import relationship

from models.base import Base


class PackageStatus(Enum):
    CREATED = 'created'
    WAREHOUSE = 'truck en route to warehouse'
    LOADING = 'truck waiting for package'
    DELIVERY = 'out for delivery'
    DELIVERED = 'delivered'


class Package(Base):
    __tablename__ = 'package'

    packageId = Column(Integer, unique=True)
    status = Column(Enum(PackageStatus), default=PackageStatus.CREATED)

    truckId = Column(Integer, ForeignKey('truck.id'))
    truck = relationship("Truck")

    userId = Column(Integer)
    x = Column(Integer)
    y = Column(Integer)

    def __init__(self, packageId, truckId, userId, x, y):
        self.packageId = packageId
        self.truckId = truckId
        self.userId = userId
        self.x = x
        self.y = y
