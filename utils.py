from datetime import date
import datetime
import json
from models import PersonaOut, TurnoOut
from database import PersonaDB, TurnoDB 

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

def to_turno_out(t: TurnoDB) -> TurnoOut:
    return TurnoOut(
        id=t.id,
        fecha=t.fecha,
        hora=t.hora,
        estado=t.estado,
        id_persona=t.id_persona

    )

#Leo los horarios del json
def leer_horarios ():
    with open ("horarios.json", "r", encoding= "utf-8") as archivo:
        horarios = json.load (archivo)
        horarios_posibles = horarios ["horarios"]
        return horarios_posibles
    

def to_time (hora: str):
        hora_time = datetime.strptime(hora, "%H:%M").time()
        return hora_time