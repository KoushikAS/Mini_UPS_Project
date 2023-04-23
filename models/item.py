from sqlalchemy import Column, Integer, ForeignKey, String
from sqlalchemy.orm import relationship

from models.base import Base


class Item(Base):
    __tablename__ = 'items'

    id = Column(Integer, primary_key=True)

    packageId = Column(Integer, ForeignKey('package.packageId'))
    package = relationship("Package")

    description = Column(String)
    count = Column(Integer)

    def __init__(self, packageId, description, count):
        self.packageId = packageId
        self.description = description
        self.count = count
