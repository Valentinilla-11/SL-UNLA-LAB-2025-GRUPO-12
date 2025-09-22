from datetime import datetime, timedelta
from fastapi import FastAPI, HTTPException, status
from database import TurnoDB, session
from models import Persona, TurnoCreate, TurnoEstadoUpdate, TurnoOut
from database import PersonaDB
import json
from sqlalchemy import func

app = FastAPI()

@app.get("/")
async def hola_mundo():
    return {"msg": "Todo funciona"}

@app.get("/personas") 
async def listar_personas(): 
    personas = session.query(PersonaDB).all() 
    return personas

@app.post("/personas",  status_code=status.HTTP_201_CREATED) 
def crear_persona(persona: Persona):
    persona_nueva = PersonaDB( 
        nombre=persona.nombre, 
        email=persona.email,
        dni=persona.dni,
        telefono=persona.telefono,
        fechaNacimiento=persona.fechaNacimiento,
        edad=persona.edad, 
    ) 
    session.add(persona_nueva) 
    try: 
        session.commit() 
        session.refresh(persona_nueva) 
    except: 
        session.rollback() 
        raise HTTPException(status_code=400, detail="Error al crear persona (email duplicado o datos inválidos)") 
    return vars(persona_nueva) 

#Post turno
@app.post("/turno", status_code=status.HTTP_201_CREATED)
def crear_turno(turno: TurnoCreate):

    #calcular los 6 meses sin cancelar turnos de una persona
    persona = session.query (PersonaDB).filter(PersonaDB.id == turno.id_persona).first()
    if not persona:
        raise HTTPException(status_code = 400, detail = "La persona a la que se le quiere asignar un turno, no esta cargada en la base de datos")
    
    limite_fecha = datetime.now() - timedelta(days=180)

    cancelados_persona = session.query(TurnoDB).filter(
        TurnoDB.id_persona == persona.id, 
        func.lower(TurnoDB.estado) == "cancelado",  
        TurnoDB.fecha >= limite_fecha
    ).count()

    if cancelados_persona >= 5:
        raise HTTPException (status_code = 400, detail = "La persona tiene 5 o mas turnos cancelados en los ultimos 6 meses por lo que no puese solicitar un nuevo turno por el momneto")
    
    #verifico si el turno ya fue tomado
    turno_tomado = session.query(TurnoDB).filter(
        TurnoDB.fecha == turno.fecha,
        TurnoDB.hora == turno.hora,
        TurnoDB.estado != "Cancelado"
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
        estado = "Pendiente",
        id_persona = turno.id_persona
    )
    
    session.add(turno_nuevo)
    try:
        session.commit()
        session.refresh(turno_nuevo)
    except:
        session.rollback()
        raise HTTPException (status_code=400, detail="Error al crear un turno")
    return vars(turno_nuevo)

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

#Leo los horarios del json
def leer_horarios ():
    with open ("horarios.json", "r", encoding= "utf-8") as archivo:
        horarios = json.load (archivo)
        horarios_posibles = horarios ["horarios"]
        return horarios_posibles

#Get turnos disponibles 
@app.get("/turnos-disponibles")
def traer_turnos_disponibles (fecha: str):

    fecha_date = datetime.strptime (fecha, "%Y-%m-%d").date() #paso a date

    #la fecha no podria ser anterior al dia en que se toma el turno
    fecha_actual = datetime.now()
    if fecha_date < fecha_actual.date():
        raise HTTPException (status_code = 400, detail = "La fecha no puede ser anterior a la fecha actual")
    
    #guardo los turnos cargados en la bd
    ocupados = session.query(TurnoDB).filter( 
        TurnoDB.fecha == fecha_date, TurnoDB.estado != "Cancelado"
    ).all()

    tomados_horas = [ocupado.hora for ocupado in ocupados] #guardo las horas de los turnos que estan en la bd
    horarios_disponibles = leer_horarios ()
    turnos_disponibles = [horario for horario in horarios_disponibles if horario not in tomados_horas] #cargo todos los horarios disponibles, van a ser los que no esten en la lista de tomados horas
    
    return {"Fecha:": fecha, "Horarios disponibles:": turnos_disponibles} 

#Patch Turno
@app.patch("/turno/{id}", response_model=TurnoOut)
def actualizar_estado_turno(id: int, turno_update: TurnoEstadoUpdate):
    turno = session.get(TurnoDB, id)
    if not turno:
        raise HTTPException(status_code=404, detail="Turno no encontrado")

    turno.estado = turno_update.estado.value 
    try:
        session.commit()
        session.refresh(turno)
    except:
        session.rollback()
        raise HTTPException(status_code=400, detail="Error al actualizar el estado del turno")

    return turno