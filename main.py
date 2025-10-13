from datetime import datetime
from fastapi import FastAPI, HTTPException, status
from models import PersonaCreate, PersonaOut, PersonaOutTurno, PersonaUpdate, TurnoOut, TurnoCreate, TurnoConPersonaOut, TurnoEstadoUpdate
from database import session, PersonaDB, TurnoDB
from utils import leer_horarios, persona_habilitada, to_persona_out, to_time, to_turno_out, calcular_edad, validar_estado, validar_estado_solo_asistido
from sqlalchemy.exc import IntegrityError
from estadoEnum import EstadoEnum

app = FastAPI()

@app.get("/")
async def root():
    return {"msg": "API funcionando"}

@app.post("/personas", response_model=PersonaOut ,status_code=status.HTTP_201_CREATED) 
def crear_persona(persona: PersonaCreate):
    try:
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
    except Exception as e: # Otro error
        session.rollback()
        raise HTTPException(status_code=400, detail=str(e))
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
    try:
        persona = session.query(PersonaDB).filter(PersonaDB.id == id).first()
        if not persona:
            raise HTTPException(status_code=404, detail="Persona no encontrada.")
        session.delete(persona)
        session.commit()
    except Exception as e:
        session.rollback()
        raise HTTPException(status_code=400, detail= str(e))
    return

@app.put("/personas/{id}", response_model=PersonaOut)
def modificar_persona(id:int, persona:PersonaCreate):
    try:
        personaCambio = session.query(PersonaDB).filter(PersonaDB.id == id).first()
        if personaCambio is None:
            raise HTTPException(status_code=404, detail="Persona no encontrada.")
        personaCambio.nombre = persona.nombre.strip() #if personaCambio.nombre is not None else None
        personaCambio.email = persona.email.lower().strip() #if personaCambio.email is not None else None
        personaCambio.dni = persona.dni #if personaCambio.dni is not None else None
        personaCambio.telefono = persona.telefono #if personaCambio.telefono is not None else None
        personaCambio.fechaNacimiento = persona.fechaNacimiento #if personaCambio.fechaNacimiento is not None else None
    
        session.commit()
        session.refresh(personaCambio)
    except IntegrityError as e: # Error de integridad (dni/mail duplicados o mail mal escrito)
        session.rollback()
        msg = str(e.orig).lower()
        if "dni" in msg:
            raise HTTPException(status_code=409, detail="El DNI ya está registrado.")
        if "email" in msg:
            raise HTTPException(status_code=409, detail="El email ya está registrado.")
        raise HTTPException(status_code=400, detail="No se pudo crear la persona (error de integridad).")
    except Exception as e:
        session.rollback()
        raise HTTPException(status_code=400, detail= str(e))

    return to_persona_out(personaCambio)

@app.patch("/personas/{id}", response_model=PersonaOut)
def patchPersona(id: int, persona: PersonaUpdate):
    try:
        personaCambio = session.query(PersonaDB).filter(PersonaDB.id == id).first()
        if personaCambio is None:
            raise HTTPException(status_code=404, detail="Persona no encontrada.")
        
        updates = persona.model_dump(exclude_unset=True)
        for campo, valor in updates.items():
            setattr(personaCambio, campo, valor)

        session.commit()
        session.refresh(personaCambio)
    except IntegrityError as e: # Error de integridad (dni/mail duplicados o mail mal escrito)
        session.rollback()
        msg = str(e.orig).lower()
        if "dni" in msg:
            raise HTTPException(status_code=409, detail="El DNI ya está registrado.")
        if "email" in msg:
            raise HTTPException(status_code=409, detail="El email ya está registrado.")
        raise HTTPException(status_code=400, detail="No se pudo crear la persona (error de integridad).")
    except Exception as e:
        session.rollback()
        raise HTTPException(status_code=400, detail= str(e))

    return to_persona_out(personaCambio)

################################## Turnos ###################################
#Post turno
@app.post("/turno", response_model=TurnoConPersonaOut, status_code=status.HTTP_201_CREATED)
def crear_turno(turno: TurnoCreate):
    try:
        #persona esta cargada en la base 
        persona = session.query (PersonaDB).filter(PersonaDB.id == turno.id_persona).first()
        if not persona:
            raise Exception("La persona a la que se le quiere asignar un turno, no esta cargada en la base de datos")
        
        #verifico si la persona esta habilitada
        if not persona_habilitada (persona, session):
            raise Exception ("La persona no esta habilitada para sacar turnos, ya que tiene 5 o mas turnos cancelados en los ultimos 6 meses")
        
        #verifico si el turno ya fue tomado
        turno_tomado = session.query(TurnoDB).filter(
            TurnoDB.fecha == turno.fecha,
            TurnoDB.hora == turno.hora,
            TurnoDB.estado != EstadoEnum.CANCELADO
        ).first ()

        if turno_tomado :
            raise Exception ("El turno ya esta tomado en esa fecha y hora")
        

        #verifico la hora
        lista_horarios = [datetime.strptime(h, "%H:%M").time() for h in leer_horarios()]#paso a time
        if turno.hora not in lista_horarios :
            raise Exception ("El horario debe estar dentro del limite horario, los horarios se organizan en intervalos de media hora, desde las 09:00 hasta las 17:00")
        
        #la fecha no podria ser anterior al dia en que se toma el turno
        fecha_actual = datetime.now()
        if turno.fecha < fecha_actual.date():
            raise Exception ( "La fecha no puede ser anterior a la fecha actual")
        
        #si no tiene errores, se crea el turno en la base
        turno_nuevo = TurnoDB(
            fecha = turno.fecha,
            hora= turno.hora, 
            estado = EstadoEnum.PENDIENTE,
            id_persona = turno.id_persona
        )
        
        session.add(turno_nuevo)
        session.commit()
        session.refresh(turno_nuevo)

        return TurnoConPersonaOut(
        id=turno_nuevo.id,
        fecha=turno_nuevo.fecha,
        hora=turno_nuevo.hora,
        estado=turno_nuevo.estado,
        persona=PersonaOutTurno(
            id=persona.id,
            nombre=persona.nombre,
            dni=persona.dni,
            fechaNacimiento=persona.fechaNacimiento,
            edad=calcular_edad(persona.fechaNacimiento)
        )
    )    
    except Exception as e:
        session.rollback()
        raise HTTPException (status_code=400, detail= str(e))
    #devuelvo con algunos de los datos de la persona

#Put turno
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

#Delete turno (fisico)
@app.delete("/turnos/{id}", status_code=status.HTTP_204_NO_CONTENT)
def eliminar_turno(id: int):
    try:
        turno = session.query(TurnoDB).filter(TurnoDB.id == id).first()
        if not turno:
            raise Exception("Turno no encontrado.")
        
        validar_estado_solo_asistido(turno)
        
        session.delete(turno)
        session.commit()
    except Exception as e:
        session.rollback()
        raise HTTPException(status_code=400, detail= str(e))
    return

#Get todos los turnos con algun dato de la persona
@app.get("/turnos", response_model=list[TurnoConPersonaOut])
async def listar_turnos_tomados():
    turnos_bd = session.query(TurnoDB, PersonaDB).join(PersonaDB).all()
    
    if not turnos_bd:
        raise HTTPException(status_code=404, detail="No hay turnos cargados.")
    
    turnos= []
    for turno, persona in turnos_bd:
        turnos.append(TurnoConPersonaOut(
            id=turno.id,
            fecha=turno.fecha,
            hora=turno.hora,
            estado=turno.estado,
            persona=PersonaOutTurno(
                id=persona.id,
                nombre=persona.nombre,
                dni=persona.dni,
                fechaNacimiento=persona.fechaNacimiento,
                edad=calcular_edad(persona.fechaNacimiento)
            )
        ))
    return turnos

#Get turnos por id
@app.get("/turno/{id}", response_model=TurnoConPersonaOut)
def traer_turno_id(id: int):
    turno = session.query(TurnoDB).filter(TurnoDB.id == id).first()
    if not turno:
        raise HTTPException(status_code=404, detail="Turno no encontrado")
    
#muestro el turno con algunos datos de la persona
    return TurnoConPersonaOut(
        id=turno.id,
        fecha=turno.fecha,
        hora=turno.hora,
        estado=turno.estado,
        persona=PersonaOutTurno(
            id=turno.persona.id,
            nombre=turno.persona.nombre,
            dni=turno.persona.dni,
            fechaNacimiento=turno.persona.fechaNacimiento,
            edad=calcular_edad(turno.persona.fechaNacimiento)
        )
    )

#Get turnos disponibles 
@app.get("/turnos-disponibles")
def traer_turnos_disponibles (fecha: str):

    try:
        fecha_date = datetime.strptime (fecha, "%Y-%m-%d").date() #paso a date
    except ValueError:
        raise HTTPException (status_code = 400, detail = "El formato de la fecha debe ser YYYY-MM-DD")

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

#Put Turno CANCELAR
@app.put("/turno/{id}/cancelar", response_model= TurnoConPersonaOut)
def actualizar_estado_turno_cancelar(id: int):
    try:
        turno = session.get(TurnoDB, id)
        if not turno:
            raise Exception("Turno no encontrado")
    
    #valido si el estado no es CANCELADO o ASISTIDO
        validar_estado(turno) 
        turno.estado = EstadoEnum.CANCELADO
        
        session.commit()
        session.refresh(turno)
    except Exception as e:
        session.rollback()
        raise HTTPException(status_code=400, detail=str(e))

    return TurnoConPersonaOut(
        id=turno.id,
        fecha=turno.fecha,
        hora=turno.hora,
        estado=turno.estado,
        persona=PersonaOutTurno(
            id=turno.persona.id,
            nombre=turno.persona.nombre,
            dni=turno.persona.dni,
            fechaNacimiento=turno.persona.fechaNacimiento,
            edad=calcular_edad(turno.persona.fechaNacimiento)
        )
    )

#Put Turno CONFIRMAR
@app.put("/turno/{id}/confirmar", response_model= TurnoConPersonaOut)
def actualizar_estado_turno_confirmar(id: int, turno_update: TurnoEstadoUpdate):
    try:
        turno = session.get(TurnoDB, id)
        if not turno:
            raise Exception("Turno no encontrado")
    
    #valido si el estado no es CANCELADO o ASISTIDO
        validar_estado(turno)

        turno.estado = EstadoEnum.CONFIRMADO
        
        session.commit()
        session.refresh(turno)
    except Exception as e:
        session.rollback()
        raise HTTPException(status_code=400, detail= str(e))

    return TurnoConPersonaOut(
        id=turno.id,
        fecha=turno.fecha,
        hora=turno.hora,
        estado=turno.estado,
        persona=PersonaOutTurno(
            id=turno.persona.id,
            nombre=turno.persona.nombre,
            dni=turno.persona.dni,
            fechaNacimiento=turno.persona.fechaNacimiento,
            edad=calcular_edad(turno.persona.fechaNacimiento)
        )
    )

#Patch Turno ASISTIDO solo para probar validaciones 
@app.patch("/turno/{id}/asistido", response_model=TurnoOut)
def actualizar_estado_turno_asistido(id: int):
    try:
        turno = session.get(TurnoDB, id)
        if not turno:
            raise Exception("Turno no encontrado")
        
        validar_estado(turno)
        turno.estado = EstadoEnum.ASISTIDO

        session.commit()
        session.refresh(turno)  
    except Exception as e:
        session.rollback()
        raise HTTPException(status_code=400, detail= str(e))
    return turno