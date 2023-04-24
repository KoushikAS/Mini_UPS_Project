import enum

from sqlalchemy import Column, Integer, Enum

from models.base import Base


class TruckStatus(enum.Enum):
    IDLE = 'idle'
    OCCUPIED = 'occupied'


class Truck(Base):
    __tablename__ = 'truck'

    id = Column(Integer, primary_key=True)
    status = Column(Enum(TruckStatus), default=TruckStatus.IDLE)
