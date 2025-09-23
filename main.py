from datetime import datetime, timedelta
from fastapi import FastAPI, HTTPException, status
from enum import EstadoEnum
from models import PersonaCreate, PersonaOut, TurnoOut, TurnoCreate, TurnoConPersonaOut, TurnoEstadoUpdate
from database import session, PersonaDB, TurnoDB
from utils import leer_horarios, to_persona_out, to_time, to_turno_out, calcular_edad
from sqlalchemy.exc import IntegrityError
from datetime import time
import json
from sqlalchemy import func

app = FastAPI()

@app.get("/")
async def root():
    return {"msg": "API funcionando"}


@app.post("/personas", response_model=PersonaOut ,status_code=status.HTTP_201_CREATED) 
def crear_persona(persona: PersonaCreate):

    dniValido = session.query(PersonaDB).filter(PersonaDB.dni == persona.dni).first()
    if dniValido:
        raise HTTPException(status_code=409, detail="El número de DNI ya está registrado.")

    emailValido = session.query(PersonaDB).filter(PersonaDB.email == persona.email).first()
    if emailValido:
        raise HTTPException(status_code=409, detail="El email ya está registrado.")

    persona_nueva = PersonaDB( 
        nombre=persona.nombre.strip(), 
        email=persona.email.lower().strip(),
        dni=persona.dni,
        telefono=persona.telefono,
        fechaNacimiento=persona.fechaNacimiento,
    ) 
    session.add(persona_nueva)
    try: # Intenta guardar la persona en la db
        session.commit()
        session.refresh(persona_nueva)
    except IntegrityError as e: # Error de integridad (dni/mail duplicados o mail mal escrito)
        session.rollback()
        msg = str(e.orig).lower()
        if "dni" in msg:
            raise HTTPException(status_code=409, detail="El DNI ya está registrado.")
        if "email" in msg:
            raise HTTPException(status_code=409, detail="El email ya está registrado.")
        raise HTTPException(status_code=400, detail="No se pudo crear la persona (error de integridad).")
    except Exception : # Otro error
        session.rollback()
        raise HTTPException(status_code=400, detail="Error al crear la persona.")
    return to_persona_out(persona_nueva)


@app.get("/personas/{id}", response_model=PersonaOut, status_code=status.HTTP_200_OK)
def listar_persona_por_id(id: int):
    persona = session.query(PersonaDB).filter(PersonaDB.id == id).first()
    if not persona:
        raise HTTPException(status_code=404, detail="Persona no encontrada.")
    return to_persona_out(persona)


@app.get("/personas") 
def listar_personas(): 
    personas = session.query(PersonaDB).all()
    personasResponse: list[PersonaOut] = []
    for persona in personas:
        personasResponse.append(to_persona_out(persona))
    return personasResponse

@app.delete("/personas/{id}", status_code=status.HTTP_204_NO_CONTENT)
def eliminar_persona(id: int):
    persona = session.query(PersonaDB).filter(PersonaDB.id == id).first()
    if not persona:
        raise HTTPException(status_code=404, detail="Persona no encontrada.")
    session.delete(persona)
    try:
        session.commit()
    except Exception:
        session.rollback()
        raise HTTPException(status_code=400, detail="Error al eliminar la persona.")
    return

@app.put("/personas/{id}", response_model=PersonaOut)
def modificar_persona(id:int, persona:PersonaCreate):
    personaCambio = session.query(PersonaDB).filter(PersonaDB.id == id).first()
    if personaCambio is None:
        raise HTTPException(status_code=404, detail="Persona no encontrada.")
    personaCambio.nombre = persona.nombre.strip() #if personaCambio.nombre is not None else None
    personaCambio.email = persona.email.lower().strip() #if personaCambio.email is not None else None
    personaCambio.dni = persona.dni #if personaCambio.dni is not None else None
    personaCambio.telefono = persona.telefono #if personaCambio.telefono is not None else None
    personaCambio.fechaNacimiento = persona.fechaNacimiento #if personaCambio.fechaNacimiento is not None else None
    try:
        session.commit()
        session.refresh(personaCambio)
    except Exception:
        session.rollback()
        raise HTTPException(status_code=400, detail="Error al modificar la persona.")

    return to_persona_out(personaCambio)


#Post turno
@app.post("/turno", response_model=TurnoConPersonaOut, status_code=status.HTTP_201_CREATED)
def crear_turno(turno: TurnoCreate):

    #calcular los 6 meses sin cancelar turnos de una persona
    persona = session.query (PersonaDB).filter(PersonaDB.id == turno.id_persona).first()
    if not persona:
        raise HTTPException(status_code = 400, detail = "La persona a la que se le quiere asignar un turno, no esta cargada en la base de datos")
    
    limite_fecha = datetime.now() - timedelta(days=180)

    cancelados_persona = session.query(TurnoDB).filter(
        TurnoDB.id_persona == persona.id, 
        TurnoDB.estado == EstadoEnum.CANCELADO,  
        TurnoDB.fecha >= limite_fecha
    ).count()

    if cancelados_persona >= 5:
        raise HTTPException (status_code = 400, detail = "La persona tiene 5 o mas turnos cancelados en los ultimos 6 meses por lo que no puese solicitar un nuevo turno por el momneto")
    
    #verifico si el turno ya fue tomado
    turno_tomado = session.query(TurnoDB).filter(
        TurnoDB.fecha == turno.fecha,
        TurnoDB.hora == turno.hora,
        TurnoDB.estado != EstadoEnum.CANCELADO
    ).first ()

    if turno_tomado :
        raise HTTPException (status_code = 400, detail ="El turno ya esta tomado en esa fecha y hora")
    
    #creo un nuevo turno 

    #verifico la hora
    lista_horarios = [datetime.strptime(h, "%H:%M").time() for h in leer_horarios()]#paso a time
    
    if turno.hora not in lista_horarios :
        raise HTTPException (status_code = 400, detail = "El horario debe estar dentro del limite horario, los horarios se organizan en intervalos de media hora, desde las 09:00 hasta las 17:00")
    
    #la fecha no podria ser anterior al dia en que se toma el turno
    fecha_actual = datetime.now()
    if turno.fecha < fecha_actual.date():
        raise HTTPException (status_code = 400, detail = "La fecha no puede ser anterior a la fecha actual")
    

    #si pasa los errores, se crea el turno en la base
    turno_nuevo = TurnoDB(
        fecha = turno.fecha,
        hora= turno.hora, 
        estado = EstadoEnum.PENDIENTE,
        id_persona = turno.id_persona
    )
    
    session.add(turno_nuevo)
    try:
        session.commit()
        session.refresh(turno_nuevo)
    except:
        session.rollback()
        raise HTTPException (status_code=400, detail="Error al crear un turno")
    #devuelvo con algunos de los datos de la persona
    return TurnoConPersonaOut(
        id=turno_nuevo.id,
        fecha=turno_nuevo.fecha,
        hora=turno_nuevo.hora,
        estado=turno_nuevo.estado,
        persona=PersonaOut(
            id=persona.id,
            nombre=persona.nombre,
            dni=persona.dni,
            fechaNacimiento=persona.fechaNacimiento,
            edad=calcular_edad(persona.fechaNacimiento)
        )
)

@app.put("/turnos/{id}", response_model=TurnoOut)
def modificar_Turno(id:int, turno:TurnoCreate):
    turnoCambio = session.query(TurnoDB).filter(TurnoDB.id == id).first()
    if turnoCambio is None:
        raise HTTPException(status_code=404, detail="Turno no encontrado.")
    turnoCambio.fecha = turno.fecha #if turnoCambio.fecha is not None else None
    turnoCambio.hora = turno.hora #if turnoCambio.hora is not None else None
    turnoCambio.estado = turno.estado #if turno.estado is not None else None
    turnoCambio.id_persona = turno.id_persona #if turnoCambio.id_persona is not None else None
    try:
        session.commit()
        session.refresh(turnoCambio)
    except Exception:
        session.rollback()
        raise HTTPException(status_code=400, detail="Error al modificar el turno.")

    return to_turno_out(turnoCambio)

@app.delete("/turnos/{id}", status_code=status.HTTP_204_NO_CONTENT)
def eliminar_turno(id: int):
    turno = session.query(TurnoDB).filter(TurnoDB.id == id).first()
    if not turno:
        raise HTTPException(status_code=404, detail="Turno no encontrado.")
    session.delete(turno)
    try:
        session.commit()
    except Exception:
        session.rollback()
        raise HTTPException(status_code=400, detail="Error al eliminar el turno.")
    return


#Get todos los turnos
@app.get("/turnos", response_model=list[TurnoOut])
async def listar_turnos_tomados():
    turnos = session.query(TurnoDB).all()
    return turnos

#Get turnos por id
@app.get("/turno/{id}", response_model=TurnoOut)
def traer_turno_id(id:int):
    turno = session.get(TurnoDB, id)
    if not turno:
        raise HTTPException(status_code=404, detail="Turno no encontrado")
    return turno

#Get turnos disponibles 
@app.get("/turnos-disponibles")
def traer_turnos_disponibles (fecha: str):

    fecha_date = datetime.strptime (fecha, "%Y-%m-%d").date() #paso a date

    #la fecha no podria ser anterior al dia en que se toma el turno
    fecha_actual = datetime.now()
    if fecha_date < fecha_actual.date():
        raise HTTPException (status_code = 400, detail = "La fecha no puede ser anterior a la fecha actual")

    ocupados = session.query(TurnoDB).filter(
        TurnoDB.fecha == fecha_date,
        TurnoDB.estado != EstadoEnum.CANCELADO
    ).all()

    #guardo los turnos cargados en la bd
    ocupados = session.query(TurnoDB).filter( 
        TurnoDB.fecha == fecha_date, TurnoDB.estado != EstadoEnum.CANCELADO
    ).all()

    tomados_horas = [ocupado.hora for ocupado in ocupados] #guardo las horas de los turnos que estan en la bd
    horarios_disponibles = [to_time(h) for h in leer_horarios ()]
    turnos_disponibles = [horario.strftime("%H:%M") for horario in horarios_disponibles if horario not in tomados_horas] #cargo todos los horarios disponibles, van a ser los que no esten en la lista de tomados horas
    
    return {"Fecha:": fecha, "Horarios disponibles:": turnos_disponibles} 

#Patch Turno CANCELAR
@app.patch("/turno/{id}/cancelar", response_model=TurnoOut)
def actualizar_estado_turno(id: int, turno_update: TurnoEstadoUpdate):
    try:
        turno = session.get(TurnoDB, id)
        if not turno:
            raise HTTPException(status_code=404, detail="Turno no encontrado")

        turno.estado = EstadoEnum.CANCELADO
        
        session.commit()
        session.refresh(turno)
    except:
        session.rollback()
        raise HTTPException(status_code=400, detail="Error al actualizar el estado del turno")

    return turno

#Patch Turno CONFIRMAR
@app.patch("/turno/{id}/confirmar", response_model=TurnoOut)
def actualizar_estado_turno(id: int, turno_update: TurnoEstadoUpdate):
    try:
        turno = session.get(TurnoDB, id)
        if not turno:
            raise HTTPException(status_code=404, detail="Turno no encontrado")

        turno.estado = EstadoEnum.CONFIRMADO
        
        session.commit()
        session.refresh(turno)
    except:
        session.rollback()
        raise HTTPException(status_code=400, detail="Error al actualizar el estado del turno")

    return turno