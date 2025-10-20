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

def obtener_persona_por_dni (dni: str, session: Session):
    persona = session.query(PersonaDB).filter(PersonaDB.dni == dni).first()
    if not persona:
        raise Exception ("La persona con DNI {} no existe". format (dni))
    
    return persona

def obtener_turnos_por_persona (id_persona: int, session: Session):
    turnos = session.query(TurnoDB).filter(TurnoDB.id_persona == id_persona).all()
    if not turnos:
        raise Exception ("La persona no tiene turnos asignados")
    return turnos

def calcular_limite_fecha(dias: int):
    limite_fecha = datetime.now() - timedelta(days=dias)
    return limite_fecha

def obtener_personas_con_turnos_cancelados(session: Session, limite_fecha: datetime, min_cancelados: int = 5):
    personas_bd = session.query(PersonaDB).all()

    if not personas_bd:
        raise Exception("No hay personas en la base de datos")
    
    personas_con_cancelados = []

    for persona in personas_bd:
        turnos_cancelados = session.query(TurnoDB).filter(
            TurnoDB.id_persona == persona.id,
            TurnoDB.estado == EstadoEnum.CANCELADO,
            TurnoDB.fecha >= limite_fecha
        ).all()

        if len(turnos_cancelados) >= min_cancelados:
            personas_con_cancelados.append({
                "persona": {
                    "id": persona.id,
                    "nombre": persona.nombre,
                    "email": persona.email,
                    "dni": str(persona.dni),
                    "telefono": persona.telefono,
                    "fecha_nacimiento": persona.fecha_nacimiento,
                    "edad": calcular_edad(persona.fecha_nacimiento),
                    "habilitado": persona.habilitado
                },
                "cantidad_cancelados": len(turnos_cancelados),
                "turnos_cancelados": [
                    {
                        "id": turno.id,
                        "fecha": turno.fecha,
                        "hora": turno.hora,
                        "estado": turno.estado
                    }
                    for turno in turnos_cancelados
                ]
            })
    return personas_con_cancelados
def obtener_turnos_entre_fechas(fechaDesde: date, fechaHasta: date, session: Session):
    
    turnos_confirmados = session.query(TurnoDB).filter(
        (TurnoDB.fecha >= fechaDesde) & (TurnoDB.fecha <= fechaHasta)
    ).all()

    if not turnos_confirmados:
        raise Exception("No hay turnos registrados entre esas fechas.")

    return turnos_confirmados

def obtener_personas_por_estado(estado: bool, session: Session):
    personas_estado = session.query(PersonaDB).filter(PersonaDB.habilitado == estado).all()

    if not personas_estado:
        raise Exception("No hay personas con ese estado.")
    
    return personas_estado
