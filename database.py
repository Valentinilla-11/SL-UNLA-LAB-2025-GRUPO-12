from sqlalchemy import create_engine, Column, Integer, String, Boolean, Date, ForeignKey, Time, Enum
from sqlalchemy.orm import declarative_base, sessionmaker 

engine = create_engine('sqlite:///tp_python.db') 

Base = declarative_base()

class PersonaDB(Base):
    __tablename__ = "personas"

    id = Column(Integer, primary_key=True)
    nombre = Column(String, nullable=False)
    email = Column(String, nullable=False, unique=True)
    dni = Column(Integer, nullable=False, unique=True)
    telefono = Column(Integer, nullable=False)
    fechaNacimiento = Column(Date, nullable=False)
    habilitado = Column(Boolean, nullable=False, default=True)
    #turnos = relationship("TurnoDB", back_populates="persona")

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
