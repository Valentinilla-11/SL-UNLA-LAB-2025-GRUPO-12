from fastapi import FastAPI, HTTPException, status
from database import session
from models import Persona

app = FastAPI()

@app.get("/")
async def hola_mundo():
    return {"msg: Todo funciona"}

@app.get("/personas") 
async def listar_personas(session): 
    personas = Persona.query.all() 
    return [vars(p) for p in personas]

@app.post("/personas",  status_code=status.HTTP_201_CREATED) 
def crear_persona(persona:Persona, session): 
    persona_nueva = Persona( 
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