from pydantic import BaseModel, EmailStr, constr, field_validator
from datetime import date
from typing import Annotated, Optional
import enum

# ---------- PERSONAS -------------

# Creamos NombreStr que acepta tildes y no permite caracteres especiales o numeros
NombreStr = Annotated[
    str, 
    constr(
    strip_whitespace=True, 
    min_length=2, 
    max_length=60, 
    pattern=r"^[A-Za-zÁÉÍÓÚáéíóúÑñüÜ ]+$"
)
]

# Clase con lo que se necesita para crear una persona
class PersonaCreate(BaseModel):
    nombre: NombreStr
    email: EmailStr
    dni: int
    telefono: int
    fechaNacimiento: date

    @field_validator("dni")
    @classmethod
    def dni_valido(cls, dniIngresado: int) -> bool:
        if dniIngresado <=0 or len(str(dniIngresado)) < 7 or len(str(dniIngresado)) > 8:
            raise ValueError("DNI invalido")
        return dniIngresado
    
    @field_validator("fechaNacimiento")
    @classmethod
    def fecha_nacimiento_valida(cls, fechaIngresada: date) -> date:
        if fechaIngresada >= date.today():
            raise ValueError("La fecha de nacimiento debe ser en el pasado.")
        return fechaIngresada





# Clase que se mostrará en el response
class PersonaOut(BaseModel):
    id: int
    nombre: str
    email: EmailStr
    dni: int
    telefono: int
    fechaNacimiento: date
    edad: int
    habilitado: bool

    class Config:
        orm_mode = True

# Clase para un patch
# class personaUpdate(BaseModel):
#    nombre: Optional[NombreStr] = None
#    email: Optional[EmailStr] = None
#    dni: Optional[int] = None
#    telefono: Optional[int] = None
#    fechaNacimiento: Optional[date] = None

# ---------- TURNOS -------------

class EstadoEnum(str, enum.Enum):
    PENDIENTE = "PENDIENTE"
    CONFIRMADO = "CONFIRMADO"
    CANCELADO = "CANCELADO"
    ASISTIDO = "ASISTIDO"

class Turno(BaseModel):
    fecha: date
    hora: str
    estado: EstadoEnum = EstadoEnum.PENDIENTE
    id_persona: int
    class Config:
        orm_mode = True

    