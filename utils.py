from datetime import date, timedelta, datetime
import json
from estadoEnum import EstadoEnum
from models import PersonaOut, TurnoOut
from database import PersonaDB, Session, TurnoDB 

def calcular_edad(fecha_nacimiento: date) -> int:
    hoy = date.today()
    edad = hoy.year - fecha_nacimiento.year

    #Si la persona no cumplió años todavía se le resta 1
    if (hoy.month, hoy.day) < (fecha_nacimiento.month, fecha_nacimiento.day):
        edad -= 1
    return edad

def to_persona_out(p: PersonaDB) -> PersonaOut:
    return PersonaOut(
        id=p.id,
        nombre=p.nombre,
        email=p.email,
        dni=p.dni,
        telefono=p.telefono,
        fecha_nacimiento=p.fecha_nacimiento,
        edad=calcular_edad(p.fecha_nacimiento),
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

# verifico si la persona esta habilitada
def persona_habilitada(persona: PersonaDB, session: Session):
    limite_fecha = datetime.now() - timedelta(days=180)

    cancelados_persona = session.query(TurnoDB).filter(
        TurnoDB.id_persona == persona.id,
        TurnoDB.estado == EstadoEnum.CANCELADO,
        TurnoDB.fecha >= limite_fecha
    ).count()

    persona.habilitado = cancelados_persona < 5
    session.commit()
    session.refresh(persona)
    return persona.habilitado

#Leo los horarios del json
def leer_horarios ():
    with open ("horarios.json", "r", encoding= "utf-8") as archivo:
        horarios = json.load (archivo)
        horarios_posibles = horarios ["horarios"]
        return horarios_posibles
    
#convierto de string a time
def to_time (hora: str):
    hora_time = datetime.strptime(hora, "%H:%M").time()
    return hora_time

#valido que el estado no sea CANCELADO o ASISTIDO
def validar_estado (turno: TurnoDB):
    if turno.estado in [EstadoEnum.CANCELADO, EstadoEnum.ASISTIDO]:
        raise Exception("No se puede modificar un turno que ya fue CANCELADO o ASISTIDO")
    return True

#valido que el estado no sea ASISTIDO (para eliminar)
def validar_estado_solo_asistido (turno: TurnoDB):
   if turno.estado == EstadoEnum.ASISTIDO:
        raise  Exception ("No se puede eliminar un turno que ya fue ASISTIDO")
   return True
