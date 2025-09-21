from fastapi import FastAPI, HTTPException, status
from database import TurnoDB, session
from models import Persona, Turno
from database import PersonaDB
import json

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


@app.get("/turnos")
async def listar_turnos_tomados():
    turnos = session.query(TurnoDB).all()
    return turnos

@app.post("/turno", status_code=status.HTTP_201_CREATED)
def crear_turno(turno:Turno):
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


@app.get("/turno/{id}")
def traer_turno_id(id:int):
    turno = session.get(TurnoDB, id)
    if not turno:
        raise HTTPException(status_code=404, detail="Turno no encontrado")
    return turno



def leer_horarios ():
    with open ("horarios.json", "r", encoding= "utf-8") as archivo:
        horarios = json.load (archivo)
        horarios_posibles = horarios ["horarios"]
