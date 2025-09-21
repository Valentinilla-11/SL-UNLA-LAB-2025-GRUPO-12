from pydantic import BaseModel
from datetime import date
import enum

class EstadoEnum(str, enum.Enum):
    PENDIENTE = "PENDIENTE"
    CONFIRMADO = "CONFIRMADO"
    CANCELADO = "CANCELADO"
    ASISTIDO = "ASISTIDO"

class Persona(BaseModel):
    nombre: str
    email: str
    dni: int
    telefono: int
    fechaNacimiento: date
    edad: int
    habilitado: bool = True
    class Config:
        orm_mode = True

class Turno(BaseModel):
    fecha: date
    hora: str
    estado: EstadoEnum = EstadoEnum.PENDIENTE
    id_persona: int
    class Config:
        orm_mode = True

    