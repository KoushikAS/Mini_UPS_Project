import sys
from sqlalchemy import MetaData, create_engine
from sqlalchemy.orm import sessionmaker, declarative_base, scoped_session
from sqlalchemy.exc import SQLAlchemyError

try:
    engine = create_engine('postgresql://postgres:Brian568@db:5432/postgres')
except Exception as e:
    print("Exception when trying to create engine.")
    print(str(e))

    sys.exit()
try:
    engine.connect()
    print("Successfully connected to existing database")
except SQLAlchemyError as err:
    print("error", err.__cause__)

m = MetaData()
m.reflect(engine)
m.drop_all(engine)

Base = declarative_base()
session_fact = sessionmaker(bind=engine)
Session = scoped_session(session_factory=session_fact)