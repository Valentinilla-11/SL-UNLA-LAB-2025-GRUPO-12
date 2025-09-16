from fastapi import FastAPI, HTTPException, status
from models import PersonaCreate, PersonaOut
from database import session, PersonaDB
from utils import to_persona_out
from sqlalchemy.exc import IntegrityError

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