from pydantic import BaseModel
from datetime import date

class Persona(BaseModel):
    nombre: str
    email: str
    dni: int
    telefono: int
    fechaNacimiento: date
    edad: int
    class Config:
        orm_mode = True

