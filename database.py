from sqlalchemy import create_engine, Column, Integer, String, Boolean, Date
from sqlalchemy.orm import declarative_base, sessionmaker 

engine = create_engine('sqlite:///tp_python.db') 

Base = declarative_base() 

class PersonaDB(Base):
    __tablename__ = "personas"

    id = Column(Integer, primary_key=True)
    nombre = Column(String)
    email = Column(String)
    dni = Column(Integer) #Hay que poner "unique" ya que el DNI es diferente
    telefono = Column(Integer)
    fechaNacimiento = Column(Date)
    edad = Column(Integer)
    estado = Column(Boolean, default=True)

Base.metadata.create_all(engine) 

Session = sessionmaker(bind=engine) 
session = Session() 

