from sqlalchemy import Column, Integer, ForeignKey, String
from sqlalchemy.orm import relationship

from models.base import Base

class Users(Base):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True)
    name = Column(String)
    email = Column(String)
    password = Column(String)
    amznid = Column(Integer)

    def __init__(self, name, email, password, amznid):
        self.name = name
        self.email = email
        self.password = password
        self.amznid = amznid