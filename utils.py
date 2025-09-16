from datetime import date
from models import PersonaOut
from database import PersonaDB

def calcular_edad(fechaNacimiento: date) -> int:
    hoy = date.today()
    edad = hoy.year - fechaNacimiento.year

    #Si la persona no cumplió años todavía se le resta 1
    if (hoy.month, hoy.day) < (fechaNacimiento.month, fechaNacimiento.day):
        edad -= 1
    return edad

def to_persona_out(p: PersonaDB) -> PersonaOut:
    return PersonaOut(
        id=p.id,
        nombre=p.nombre,
        email=p.email,
        dni=p.dni,
        telefono=p.telefono,
        fechaNacimiento=p.fechaNacimiento,
        edad=calcular_edad(p.fechaNacimiento),
        habilitado=p.habilitado
    )