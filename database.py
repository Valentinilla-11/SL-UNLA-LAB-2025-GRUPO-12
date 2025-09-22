from sqlalchemy import create_engine, Column, Integer, String, Boolean, Date, ForeignKey, Time
from sqlalchemy.orm import declarative_base, sessionmaker 

engine = create_engine('sqlite:///tp_python.db') 

Base = declarative_base()

class PersonaDB(Base):
    __tablename__ = "personas"

    id = Column(Integer, primary_key=True)
    nombre = Column(String)
    email = Column(String)
    dni = Column(Integer, unique=True)
    telefono = Column(Integer)
    fechaNacimiento = Column(Date)
    edad = Column(Integer)
    estado = Column(Boolean, default=True)

class TurnoDB(Base):
    __tablename__ = "turnos"

    id = Column(Integer, primary_key=True)
    fecha = Column(Date)
    hora = Column(Time, nullable = False)
    estado = Column(String, default="PENDIENTE")
    id_persona = Column(Integer, ForeignKey("personas.id"))

Base.metadata.create_all(engine) 

Session = sessionmaker(bind=engine) 
session = Session() 
