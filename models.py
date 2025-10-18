from pydantic import BaseModel, EmailStr, constr, field_validator
from datetime import date, time
from typing import Annotated, Optional, List
from estadoEnum import EstadoEnum

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
    fecha_nacimiento: date

    @field_validator("dni")
    @classmethod
    def dni_valido(cls, dni_ingresado: int) -> int:
        if dni_ingresado <=0 or len(str(dni_ingresado)) < 7 or len(str(dni_ingresado)) > 8:
            raise ValueError("DNI invalido")
        return dni_ingresado
    
    @field_validator("fecha_nacimiento")
    @classmethod
    def fecha_nacimiento_valida(cls, fecha_ingresada: date) -> date:
        if fecha_ingresada >= date.today():
            raise ValueError("La fecha de nacimiento debe ser en el pasado.")
        return fecha_ingresada


# Clase que se mostrará en el response
class PersonaOut(BaseModel):
    id: int
    nombre: str
    email: EmailStr
    dni: int
    telefono: int
    fecha_nacimiento: date
    edad: int
    habilitado: bool

    class Config:
        orm_mode = True

class PersonaOutTurno (BaseModel):
    id: int
    nombre: str
    dni: int
    fecha_nacimiento: date
    edad: int

# Clase para un patch
class PersonaUpdate(BaseModel):
    nombre: Optional[NombreStr] = None
    email: Optional[EmailStr] = None
    dni: Optional[int] = None
    telefono: Optional[int] = None
    fecha_nacimiento: Optional[date] = None

# ---------- TURNOS -------------

class TurnoCreate(BaseModel):
    fecha: date
    hora: time
    estado: EstadoEnum=EstadoEnum.PENDIENTE
    id_persona: int  # Solo se envía el ID, no el objeto completo


class TurnoConPersonaOut(BaseModel):
    id: int
    fecha: date
    hora: time
    estado: str
    persona: PersonaOutTurno 

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
    
#para patch de estado
class TurnoEstadoUpdate(BaseModel):
    estado: EstadoEnum

#Para mostrar el reporte de personas con turnos por dni 
class PersonaConTurnosOut(BaseModel):
    id: int
    nombre: str
    dni: str
    fecha_nacimiento: date
    edad: int
    habilitado: bool
    turnos: List[TurnoOut] = []