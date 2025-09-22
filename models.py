from typing import Optional
from pydantic import BaseModel
from datetime import date, time
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

class TurnoCreate(BaseModel):
    fecha: date
    hora: time
    estado: EstadoEnum=EstadoEnum.PENDIENTE
    id_persona: int  # Solo se envía el ID, no el objeto completo

class TurnoOut(BaseModel):
    id: int
    fecha: date
    hora: time
    estado: str
    id_persona: int
    class Config:
        orm_mode = True

class TurnoUpdate(BaseModel):
    fecha: Optional[date]
    hora: Optional[time]
    estado: Optional[EstadoEnum]
    id_persona: Optional[int]
    