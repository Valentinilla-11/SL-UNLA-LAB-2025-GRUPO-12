from ctypes import alignment
from datetime import datetime, timedelta, date
from io import BytesIO
from fastapi import FastAPI, HTTPException, status
from fastapi.responses import FileResponse, StreamingResponse
from models import PersonaConTurnosOut, PersonaCreate, PersonaOut, PersonaOutTurno, PersonaUpdate, TurnoOut, TurnoCreate, TurnoConPersonaOut, TurnoEstadoUpdate
from database import session, PersonaDB, TurnoDB
from utils import *
from sqlalchemy.exc import IntegrityError
from sqlalchemy import Table, extract
from estadoEnum import EstadoEnum
from fastapi import HTTPException, Query
from math import ceil
from dotenv import load_dotenv
import pandas as pd
import os
from borb.pdf import Document, Page, Paragraph, PDF, FixedColumnWidthTable, SingleColumnLayout, PageLayout, LayoutElement, X11Color, HexColor, Table, FlexibleColumnWidthTable
from borb.pdf.layout_element.layout_element import LayoutElement

app = FastAPI()

load_dotenv()
#uso las variables de entorno para los dias y validacion de minimos cancelados 
DIAS_TURNOS_CANCELADOS = int(os.getenv("DIAS_TURNOS_CANCELADOS", 180))
MIN_CANCELADOS = int(os.getenv("MIN_CANCELADOS", 1))
#variable de entorno para paginacion
REGISTROS_POR_PAGINA = int(os.getenv("REGISTROS_POR_PAGINA", 5))


@app.get("/")
async def root():
    return {"msg": "API funcionando"}

@app.post("/personas", response_model=PersonaOut ,status_code=status.HTTP_201_CREATED) 
def crear_persona(persona: PersonaCreate):
    try:
        dni_valido = session.query(PersonaDB).filter(PersonaDB.dni == persona.dni).first()
        if dni_valido:
            raise HTTPException(status_code=409, detail="El número de DNI ya está registrado.")

        email_valido = session.query(PersonaDB).filter(PersonaDB.email == persona.email).first()
        if email_valido:
            raise HTTPException(status_code=409, detail="El email ya está registrado.")

        persona_nueva = PersonaDB( 
            nombre=persona.nombre.strip(), 
            email=persona.email.lower().strip(),
            dni=persona.dni,
            telefono=persona.telefono,
            fecha_nacimiento=persona.fecha_nacimiento,
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
        persona_cambio = session.query(PersonaDB).filter(PersonaDB.id == id).first()
        if persona_cambio is None:
            raise HTTPException(status_code=404, detail="Persona no encontrada.")
        persona_cambio.nombre = persona.nombre.strip() #if personaCambio.nombre is not None else None
        persona_cambio.email = persona.email.lower().strip() #if personaCambio.email is not None else None
        persona_cambio.dni = persona.dni #if personaCambio.dni is not None else None
        persona_cambio.telefono = persona.telefono #if personaCambio.telefono is not None else None
        persona_cambio.fecha_nacimiento = persona.fecha_nacimiento #if personaCambio.fechaNacimiento is not None else None
    
        session.commit()
        session.refresh(persona_cambio)
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

    return to_persona_out(persona_cambio)

@app.patch("/personas/{id}", response_model=PersonaOut)
def patchPersona(id: int, persona: PersonaUpdate):
    try:
        persona_cambio = session.query(PersonaDB).filter(PersonaDB.id == id).first()
        if persona_cambio is None:
            raise HTTPException(status_code=404, detail="Persona no encontrada.")
        
        updates = persona.model_dump(exclude_unset=True)
        for campo, valor in updates.items():
            setattr(persona_cambio, campo, valor)

        session.commit()
        session.refresh(persona_cambio)
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

    return to_persona_out(persona_cambio)

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
        lista_horarios = leer_horarios_env() #leo del .env
        #lista_horarios = [datetime.strptime(h, "%H:%M").time() for h in leer_horarios()]#paso a time
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
            fecha_nacimiento=persona.fecha_nacimiento,
            edad=calcular_edad(persona.fecha_nacimiento)
        )
    )    
    except Exception as e:
        session.rollback()
        raise HTTPException (status_code=400, detail= str(e))
    #devuelvo con algunos de los datos de la persona

#Put turno
@app.put("/turnos/{id}", response_model=TurnoOut)
def modificar_Turno(id:int, turno:TurnoCreate):
    turno_cambio = session.query(TurnoDB).filter(TurnoDB.id == id).first()
    if turno_cambio is None:
        raise HTTPException(status_code=404, detail="Turno no encontrado.")
    turno_cambio.fecha = turno.fecha #if turnoCambio.fecha is not None else None
    turno_cambio.hora = turno.hora #if turnoCambio.hora is not None else None
    turno_cambio.estado = turno.estado #if turno.estado is not None else None
    turno_cambio.id_persona = turno.id_persona #if turnoCambio.id_persona is not None else None
    try:
        session.commit()
        session.refresh(turno_cambio)
    except Exception:
        session.rollback()
        raise HTTPException(status_code=400, detail="Error al modificar el turno.")

    return to_turno_out(turno_cambio)

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
                fecha_nacimiento=persona.fecha_nacimiento,
                edad=calcular_edad(persona.fecha_nacimiento)
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
            fecha_nacimiento=turno.persona.fecha_nacimiento,
            edad=calcular_edad(turno.persona.fecha_nacimiento)
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
    horarios_disponibles = leer_horarios_env() #leo del .env
    #horarios_disponibles = [to_time(h) for h in leer_horarios ()]
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
        
        persona_db = session.query (PersonaDB).filter(PersonaDB.id == turno.id_persona).first()
        habilitada_persona= persona_habilitada (persona_db, session) 

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
            fecha_nacimiento=turno.persona.fecha_nacimiento,
            edad=calcular_edad(turno.persona.fecha_nacimiento)
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
            fecha_nacimiento=turno.persona.fecha_nacimiento,
            edad=calcular_edad(turno.persona.fecha_nacimiento)
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


#Punto E REPORTES

@app.get("/reportes/turnos-por-persona/{dni}")
def reportes_turnos_por_persona( dni: int, pagina: int = 1, cant_por_pag: int = REGISTROS_POR_PAGINA):
    try:
        persona = obtener_persona_por_dni(dni, session)
        turnos_bd = obtener_turnos_por_persona(persona.id, session)

        turnos = [
            {
                "id": turno.id,
                "fecha": turno.fecha,
                "hora": turno.hora,
                "estado": turno.estado,
                "id_persona": turno.id_persona
            }
            for turno in turnos_bd
        ]

        paginas = ceil(len(turnos) / cant_por_pag) if len(turnos) else 1
        inicio = (pagina - 1) * cant_por_pag
        fin = inicio + cant_por_pag
        turnos_paginados = turnos[inicio:fin]

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

    return {
        "paginado": {
            "pagina": pagina,
            "cantidad_turnos_pag": cant_por_pag,
            "total_turnos": len(turnos),
            "total_paginas": paginas
        },
        "persona": {
            "id": persona.id,
            "nombre": persona.nombre,
            "dni": str(persona.dni),
            "fecha_nacimiento": persona.fecha_nacimiento,
            "edad": calcular_edad(persona.fecha_nacimiento),
            "habilitado": persona.habilitado
        },

        "turnos": turnos_paginados
    }

#GET /reportes/turnos-cancelados?min=int
@app.get("/reportes/turnos-cancelados")
def reportes_personas_con_turnos_cancelados(min: int = MIN_CANCELADOS, dias: int = DIAS_TURNOS_CANCELADOS, pagina: int = 1, cant_por_pag: int = REGISTROS_POR_PAGINA):

    limite = calcular_limite_fecha(dias)
    personas = obtener_personas_con_turnos_cancelados(session, limite, min)

    #Aplico la paginacion sobre las personas, no sobre los turnos 

    paginas = ceil(len(personas) / cant_por_pag) if len(personas) else 1
    inicio = (pagina - 1) * cant_por_pag
    fin = inicio + cant_por_pag
    personas_paginadas = personas[inicio:fin]

    return {
        "paginado": {
            "pagina": pagina,
            "cant_personas_pagina": cant_por_pag,
            "total_personas": len(personas),
            "total_paginas": paginas
        },
        "personas": personas_paginadas
    }


@app.get("/reportes/turnos-por-fecha")
def turnos_por_fecha(fecha: date, pagina: int = 1, cant_por_pag: int = REGISTROS_POR_PAGINA):

    turnos = session.query(TurnoDB).join(PersonaDB).filter(TurnoDB.fecha == fecha).all()

    resultado = []
    for turno in turnos:
        persona = turno.persona
        persona_out = PersonaOutTurno(
            id=persona.id,
            nombre=persona.nombre,
            dni=persona.dni,
            fecha_nacimiento=persona.fecha_nacimiento,
            edad=calcular_edad(persona.fecha_nacimiento)
        )
        resultado.append(
            TurnoConPersonaOut(
                id=turno.id,
                fecha=turno.fecha,
                hora=turno.hora,
                estado=turno.estado,
                persona=persona_out
            )
        )
    
    paginas = ceil(len(resultado) / cant_por_pag) if len(resultado) else 1
    inicio = (pagina - 1) * cant_por_pag
    fin = inicio + cant_por_pag
    resultado_paginado = resultado[inicio:fin]

    if not resultado:
        raise HTTPException(status_code=404, detail="No hay Turnos cargados para esa fecha.")
    return {
        "paginado": {
            "pagina": pagina,
            "cant_turnos_pagina": cant_por_pag,
            "total_turnos": len(resultado),
            "total_paginas": paginas
        },
        "turnos": resultado_paginado
    }

@app.get("/reportes/turnos-cancelados-por-mes")
def turnos_cancelados_por_mes(pagina: int = 1, cant_por_pag: int = REGISTROS_POR_PAGINA):
    hoy = datetime.today()
    mes_actual = hoy.month
    anio_actual = hoy.year

    turnos = session.query(TurnoDB).filter(
        TurnoDB.estado == "CANCELADO",
        extract("month", TurnoDB.fecha) == mes_actual,
        extract("year", TurnoDB.fecha) == anio_actual
    ).all()

    resultado = {
        "anio": anio_actual,
        "mes": mes_actual,
        "cantidad": len(turnos),
        "turnos": []
    }

    for turno in turnos:
        resultado["turnos"].append({
            "id": turno.id,
            "persona_id": turno.id_persona,
            "fecha": turno.fecha,
            "hora": turno.hora.strftime("%H:%M"),
            "estado": turno.estado
        })

    paginas = ceil(len(resultado) / cant_por_pag) if len(resultado) else 1
    inicio = (pagina - 1) * cant_por_pag
    fin = inicio + cant_por_pag
    turnos_paginados = resultado ["turnos"] [inicio:fin]

    if not resultado:
        raise HTTPException(status_code=404, detail="No hay Turnos cancelados para ese mes.")
    return {
        "paginado": {
            "pagina": pagina,
            "cant_turnos_pagina": cant_por_pag,
            "total_turnos": len(resultado["turnos"]),
            "total_paginas": paginas
        },
        "turnos": turnos_paginados
    }

# GET /reportes/turnos-confirmados?desde=YYYY-MM-DD&hasta=YYYY-MM-DD
@app.get("/reportes/turnos-confirmados")
def reportes_turnos_entre_fechas(
    desde: date, 
    hasta: date, 
    page: int = Query(1, ge=1), 
):
    size = int(os.environ["REGISTROS_POR_PAGINA"])
    try:
        turnos_por_fecha = obtener_turnos_entre_fechas(desde, hasta, session)
        turnos_confirmados = obtener_turnos_por_persona_con_lista(turnos_por_fecha, session)
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))
    
    items = len(turnos_confirmados)
    pages = ceil(items / size) if items else 1
    inicio = (page - 1) * size
    fin = inicio + size
    response = turnos_confirmados[inicio:fin]

    return {
        "meta": {
            "page": page,
            "size": size,
            "items": items,
            "pages": pages,
        },
        "data": response
    }
        

# GET /reportes/estado-personas?habilitada=true/false
@app.get("/reportes/estado-personas")
def reportes_personas_estado_habilitacion(habilitada: bool, pagina: int = 1, cant_por_pag: int = REGISTROS_POR_PAGINA):
    try:
        personas_por_estado = obtener_personas_por_estado(habilitada, session)
    except Exception as e:
        raise HTTPException(status_code=404,detail=str(e))
    
    paginas = ceil(len(personas_por_estado) / cant_por_pag) if len(personas_por_estado) else 1
    inicio = (pagina - 1) * cant_por_pag
    fin = inicio + cant_por_pag
    personas_paginadas = personas_por_estado[inicio:fin]
    
    return {
        "paginado": {
            "pagina": pagina,
            "cant_personas_pagina": cant_por_pag,
            "total_personas": len(personas_por_estado),
            "total_paginas": paginas
        },
        "personas": personas_paginadas
    }
    
#Punto f y g Reportes csv y pdf
# GET /reportes/csv/turnos-confirmados?desde=YYYY-MM-DD&hasta=YYYY-MM-DD
@app.get("/reportes/csv/turnos-confirmados")
def csv_turnos_confirmados(desde: date, hasta: date):
    try:
        turnos_por_fecha = obtener_turnos_entre_fechas(desde, hasta, session)
        personas_con_turnos = obtener_turnos_por_persona_con_lista(turnos_por_fecha, session)
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))
    
    filas = []
    for persona in personas_con_turnos:
        for turno in persona.turnos:
            filas.append({
                "fecha_turno": turno.fecha,
                "hora_turno": turno.hora,
                "estado": turno.estado,
                "persona": persona.nombre,
                "dni": persona.dni
            })

    df = pd.DataFrame(filas)

    nombre_archivo = "turnos_confirmados_por_fecha.csv"
    df.to_csv(nombre_archivo, index=False)

    return FileResponse(
        nombre_archivo,
        media_type="text/csv",
        filename=nombre_archivo
    )

# GET /reportes/csv/estado-personas
@app.get("/reportes/csv/estado-personas")
def csv_estado_personas(habilitada: bool):
    try:
        personas = obtener_personas_por_estado(habilitada, session)
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))
    
    filas = []
    for persona in personas:
        filas.append({
            "nombre": persona.nombre,
            "dni": persona.dni,
            "habilitado": persona.habilitado
        })

    df = pd.DataFrame(filas)

    nombre_archivo = "estado_personas.csv"
    df.to_csv(nombre_archivo, index=False)

    return FileResponse(
        nombre_archivo,
        media_type="text/csv",
        filename=nombre_archivo
    )

# GET /reportes/pdf/turnos-confirmados?desde=YYYY-MM-DD&hasta=YYYY-MM-DD
@app.get("/reportes/pdf/turnos-confirmados")
def pdf_turnos_confirmados(desde: date, hasta: date):
    try:
        turnos_por_fecha = obtener_turnos_entre_fechas(desde, hasta, session)
        personas_con_turnos = obtener_turnos_por_persona_con_lista(turnos_por_fecha, session)
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))
    
    filas = []
    for persona in personas_con_turnos:
        for turno in persona.turnos:
            filas.append({
                "fecha_turno": turno.fecha,
                "hora_turno": turno.hora,
                "estado": turno.estado,
                "persona": persona.nombre,
                "dni": persona.dni
            })
    
    df = pd.DataFrame(filas)

    doc = Document()
    page = Page()
    doc.append_page(page)
    layout = SingleColumnLayout(page)

    titulo = Paragraph("Reporte de TODOS los turnos confirmados", font_size=18)
    layout.append_layout_element(titulo)

    tabla = FixedColumnWidthTable(
        number_of_rows= len(df) + 1,
        number_of_columns= len(df.columns)
    )

    columnas = ["FECHA", "HORA", "ESTADO", "PACIENTE", "DNI"]
    for col in columnas:
        tabla.append_layout_element(Table.TableCell(Paragraph(col), background_color=HexColor("#BBDEFB")))

    for fila in filas:
        tabla.append_layout_element(Paragraph(str(fila["fecha_turno"])))
        tabla.append_layout_element(Paragraph(str(fila["hora_turno"])))
        tabla.append_layout_element(Paragraph(str(fila["estado"])))
        tabla.append_layout_element(Paragraph(str(fila["persona"])))
        tabla.append_layout_element(Paragraph(str(fila["dni"])))

    tabla.set_padding_on_all_cells(padding_bottom=3, padding_left=3, padding_right=3, padding_top=3)
    
    layout.append_layout_element(tabla)

    nombre_archivo = "turnos_confirmados_por_fecha.pdf"
    
    PDF.write(what=doc, where_to=nombre_archivo)

    return FileResponse(
        nombre_archivo,
        media_type="application/pdf",
        filename=nombre_archivo
    )

# GET /reportes/pdf/estado-personas
@app.get("/reportes/pdf/estado-personas")
def csv_estado_personas(habilitada: bool):
    try:
        personas = obtener_personas_por_estado(habilitada, session)
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))
    
    filas = []
    for persona in personas:
        filas.append({
            "nombre": persona.nombre,
            "dni": persona.dni,
            "habilitado": persona.habilitado
        })

    df = pd.DataFrame(filas)

    doc = Document()
    page = Page()
    doc.append_page(page)
    layout = SingleColumnLayout(page)

    titulo = Paragraph("Reporte de estados de las personas", font_size=18)
    layout.append_layout_element(titulo)

    tabla = FixedColumnWidthTable(
        number_of_rows= len(df) + 1,
        number_of_columns= len(df.columns)
    )

    columnas = ["NOMBRE", "DNI", "HABILITADO"]
    for col in columnas:
        tabla.append_layout_element(Table.TableCell(Paragraph(col), background_color=HexColor("#BBDEFB")))

    for _, row in df.iterrows():
        for value in row:
            tabla.append_layout_element(Paragraph(str(value)))

    tabla.set_padding_on_all_cells(padding_bottom=3, padding_left=3, padding_right=3, padding_top=3)

    layout.append_layout_element(tabla)

    nombre_archivo = "estado_personas.pdf"
    
    PDF.write(what=doc, where_to=nombre_archivo)

    return FileResponse(
        nombre_archivo,
        media_type="application/pdf",
        filename=nombre_archivo
    )


#csv turnos por persona
@app.get("/reportes/turnos-por-persona-csv/{dni}")
def turnos_por_persona_csv(dni: int):
    try:
        persona = obtener_persona_por_dni(dni, session)
        turnos_bd = obtener_turnos_por_persona(persona.id, session)

    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))
    
    datos = []

    for turno in turnos_bd:
        datos.append({
            "id_turnos": turno.id ,
            "fecha_turno": turno.fecha ,
            "hora_turno": turno.hora,
            "estado": turno.estado ,
            "id_persona": turno.id_persona
        })
    archivo = f"turnos_persona_{dni}.csv"
    df = pd.DataFrame(datos)
    df.to_csv(archivo, index=False)

    return FileResponse(
        archivo,
        media_type="text/csv",
        filename= archivo
    )

#csv turnos cancelados
@app.get("/reportes/turnos-cancelados-min-csv")
def personas_con_turnos_cancelados_csv(min: int = MIN_CANCELADOS, dias: int = DIAS_TURNOS_CANCELADOS):
    try:
        limite = calcular_limite_fecha(dias)
        personas = obtener_personas_con_turnos_cancelados(session, limite, min)

        if not personas:
            raise HTTPException(status_code=404, detail="No hay personas con turnos cancelados.")

        datos = []
        for item in personas: 
            persona = item["persona"]
            for turno in item["turnos_cancelados"]:
                datos.append({
                    "id_persona": persona["id"],
                    "nombre": persona["nombre"],
                    "DNI": persona["dni"],
                    "habilitado": persona["habilitado"],
                    "id_turno": turno["id"],
                    "fecha": turno["fecha"],
                    "hora": turno["hora"].strftime("%H:%M"),
                    "estado": turno["estado"]
                })

        archivo = f"personas_con_turnos_cancelados_min_{min}.csv"
        df = pd.DataFrame(datos)
        df.to_csv(archivo, index=False)

        return FileResponse(
            archivo,
            media_type="text/csv",
            filename= archivo
        )

    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))

#pdf turnos por persona
@app.get("/reportes/turnos-por-persona-pdf/{dni}")
def turnos_por_persona_pdf(dni: int, cant_por_pag: int = REGISTROS_POR_PAGINA):
    try:
        persona = obtener_persona_por_dni(dni, session)
        turnos_bd = obtener_turnos_por_persona(persona.id, session)

    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))
    
    #creo un solo documento con varias paginas
    documento = Document()
    paginas = ceil(len(turnos_bd) / cant_por_pag) if len(turnos_bd) else 1
    
    #hago el for para cargar todas las paginas en el mismo documento
    for num_pagina in range(1, paginas + 1):
        pagina = Page()
        documento.append_page(pagina)

        inicio = (num_pagina - 1) * cant_por_pag
        fin = inicio + cant_por_pag
        turnos_paginados = turnos_bd[inicio:fin]

        disenio: PageLayout = SingleColumnLayout(pagina)

        titulo = Paragraph("Reporte de turnos por persona", font_size=18, font="Helvetica-Bold")
        disenio.append_layout_element(titulo)

        datos_persona = Paragraph(f"Nombre: {persona.nombre} | DNI: {persona.dni}", font_size=14, font="Helvetica-Bold")
        disenio.append_layout_element(datos_persona)

        filas = max(len(turnos_paginados), 1) + 1

        tabla = FixedColumnWidthTable(
            number_of_columns=3,
            number_of_rows= filas
        )
        #encabezados de columnas
        columnas = ["Fecha", "Hora", "Estado"]
        for col in columnas:
            #agrego color al fondo de los encabezados nada mas
            tabla.append_layout_element(Table.TableCell(Paragraph(col), background_color=HexColor("#BBDEFB")))

        for fila in turnos_paginados:
            tabla.append_layout_element(Paragraph(str(fila.fecha)))
            tabla.append_layout_element(Paragraph(str(fila.hora)))
            tabla.append_layout_element(Paragraph(str(fila.estado)))

        #agrega espacios para que la tabla quede mas prolija
        tabla.set_padding_on_all_cells(padding_bottom=3, padding_left=3, padding_right=3, padding_top=3)

        disenio.append_layout_element(tabla)

        #info de la paginacion
        disenio.append_layout_element(Paragraph(f"Página {num_pagina}" , font_size=12))
        disenio.append_layout_element(Paragraph(f"Cantidad de turnos por pagina {cant_por_pag}  | Total de turnos {len(turnos_bd)} | Cantidad de paginas {paginas}", font_size=12))
    
    archivo_pdf = f"turnos_persona_{dni}.pdf"
    PDF.write(what=documento, where_to=archivo_pdf)

    return FileResponse(
        archivo_pdf,
        media_type="application/pdf",
        filename= archivo_pdf
    )

#pdf turnos cancelados 
@app.get("/reportes/turnos-cancelados-min-pdf")
def personas_con_turnos_cancelados_pdf(min: int = MIN_CANCELADOS, dias: int = DIAS_TURNOS_CANCELADOS, cant_por_pag: int = REGISTROS_POR_PAGINA):
    try:
        limite = calcular_limite_fecha(dias)
        personas = obtener_personas_con_turnos_cancelados(session, limite, min)

    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))

    documento = Document()
    paginas = ceil(len(personas) / cant_por_pag) if len(personas) else 1

    for num_pagina in range(1, paginas + 1):
        pagina = Page()
        documento.append_page(pagina)

        inicio = (num_pagina - 1) * cant_por_pag
        fin = inicio + cant_por_pag
        personas_paginadas = personas[inicio:fin]

        disenio: PageLayout = SingleColumnLayout(pagina)

        titulo = Paragraph("Reporte de personas con turnos cancelados", font_size=18, font="Helvetica-Bold")
        disenio.append_layout_element(titulo)

        if not personas_paginadas:
            disenio.append_layout_element(
                Paragraph("No hay personas con turnos cancelados.", font_size=14)
            )
            continue

        
        for item in personas_paginadas:
            persona = item["persona"]
            turnos = item["turnos_cancelados"]
            
            #primero pongo los datos de la persona y despues una tabla con los turnos cancelados
            disenio.append_layout_element(Paragraph(f"Nombre: {persona['nombre']} | DNI: {persona['dni']} | Habilitado: {persona['habilitado']}",font_size=14 , font="Helvetica-Bold"))

            #si no tiuene turnos
            if not turnos:
                disenio.append_layout_element(Paragraph("No tiene turnos cancelados.", font_size=12))
                continue

            #tabla solo con los turnos 
            tabla = FixedColumnWidthTable(number_of_columns=3, number_of_rows=len(turnos)+1)

            #encabezados
            for col in ["Fecha", "Hora", "Estado"]:
                tabla.append_layout_element(Table.TableCell(Paragraph(col), background_color=HexColor("#BBDEFB"))) 

            #filas
            for turno in turnos:
                tabla.append_layout_element(Paragraph(str(turno["fecha"])))
                tabla.append_layout_element(Paragraph(str(turno["hora"].strftime("%H:%M"))))
                tabla.append_layout_element(Paragraph(str(turno["estado"])))

            # agrega espacios para que la tabla quede mas prolija
            tabla.set_padding_on_all_cells(padding_bottom=3, padding_left=3, padding_right=3, padding_top=3)

            disenio.append_layout_element(tabla)

        #info de la paginacion
        disenio.append_layout_element(Paragraph(f"Página {num_pagina}" , font_size=12))
        disenio.append_layout_element(Paragraph(f"Cantidad de personas por pagina {cant_por_pag}  | Cantidad de personas {len(personas)} | Cantidad de paginas {paginas}", font_size=12))
    

    archivo_pdf = f"personas_con_turnos_cancelados_min_{min}.pdf"
    PDF.write(what=documento, where_to=archivo_pdf)

    return FileResponse(
        archivo_pdf,
        media_type="application/pdf",
        filename= archivo_pdf
    )

@app.get("/reportes/turnos-por-fecha-csv/{fecha}")
def turnos_por_fecha_csv(fecha: date):
    try:
        turnos_bd = (
            session.query(TurnoDB)
            .join(PersonaDB)
            .filter(TurnoDB.fecha == fecha)
            .all()
        )

        if not turnos_bd:
            raise Exception("No hay turnos para esa fecha")

    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))

    datos = []
    for turno in turnos_bd:
        persona = turno.persona
        datos.append({
            "fecha_turno": turno.fecha,
            "hora_turno": turno.hora.strftime("%H:%M") if turno.hora else "",
            "estado": turno.estado,
            "nombre": persona.nombre,
            "dni": persona.dni
        })

    archivo = f"turnos_fecha_{fecha}.csv"
    df = pd.DataFrame(datos)
    df.to_csv(archivo, index=False)

    return FileResponse(
        archivo,
        media_type="text/csv",
        filename=archivo
    )


@app.get("/reportes/turnos-por-fecha-pdf/{fecha}")
def turnos_por_fecha_pdf(fecha: date):
    archivo_csv = turnos_por_fecha_csv(fecha).filename
    df = pd.read_csv(archivo_csv)

    documento = Document()
    pagina = Page()
    documento.append_page(pagina)
    disenio: PageLayout = SingleColumnLayout(pagina)

    titulo = Paragraph(f"Turnos del día {fecha}", font_size=18)
    disenio.append_layout_element(titulo)

    tabla = FixedColumnWidthTable(number_of_columns=len(df.columns), number_of_rows=len(df)+1)

    columnas = ["FECHA", "HORA", "ESTADO", "PACIENTE", "DNI"]

    for col in columnas:
        tabla.append_layout_element(Table.TableCell(Paragraph(col), background_color=HexColor("#BBDEFB")))

    for _, fila in df.iterrows():
        for valor in fila:
            tabla.append_layout_element(Paragraph(str(valor)))

    tabla.set_padding_on_all_cells(padding_bottom=3, padding_left=3, padding_right=3, padding_top=3)

    disenio.append_layout_element(tabla)

    archivo_pdf = f"turnos_fecha_{fecha}.pdf"
    PDF.write(what=documento, where_to=archivo_pdf)

    return FileResponse(
        archivo_pdf,
        media_type="application/pdf",
        filename=archivo_pdf
    )

@app.get("/reportes/turnos-cancelados-por-mes-csv")
def turnos_cancelados_por_mes_csv():
    hoy = datetime.today()
    mes_actual = hoy.month
    anio_actual = hoy.year

    try:
        turnos_bd = session.query(TurnoDB).filter(
            TurnoDB.estado == "CANCELADO",
            extract("month", TurnoDB.fecha) == mes_actual,
            extract("year", TurnoDB.fecha) == anio_actual
        ).all()
        if not turnos_bd:
            raise Exception("No hay turnos cancelados para este mes")
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))

    datos = []
    for turno in turnos_bd:
        persona = session.query(PersonaDB).filter(PersonaDB.id == turno.id_persona).first()
        datos.append({
            "fecha_turno": turno.fecha,
            "hora_turno": turno.hora.strftime("%H:%M"),
            "estado": turno.estado,
            "nombre": persona.nombre
        })

    archivo = f"turnos_cancelados_{anio_actual}_{mes_actual}.csv"
    df = pd.DataFrame(datos)
    df.to_csv(archivo, index=False)

    return FileResponse(
        archivo,
        media_type="text/csv",
        filename=archivo
    )

@app.get("/reportes/turnos-cancelados-por-mes-pdf")
def turnos_cancelados_por_mes_pdf():
    hoy = datetime.today()
    mes_actual = hoy.month
    anio_actual = hoy.year

    archivo_csv = turnos_cancelados_por_mes_csv().filename
    df = pd.read_csv(archivo_csv)

    documento = Document()
    pagina = Page()
    documento.append_page(pagina)
    disenio: PageLayout = SingleColumnLayout(pagina)

    titulo = Paragraph(f"Turnos cancelados - {mes_actual}/{anio_actual}", font_size=18)
    disenio.append_layout_element(titulo)

    tabla = FixedColumnWidthTable(number_of_columns=len(df.columns), number_of_rows=len(df)+1)

    columnas = ["FECHA", "HORA", "ESTADO", "PACIENTE"]

    for col in columnas:
        tabla.append_layout_element(Table.TableCell(Paragraph(col), background_color=HexColor("#BBDEFB")))

    for _, fila in df.iterrows():
        for valor in fila:
            tabla.append_layout_element(Paragraph(str(valor)))

    tabla.set_padding_on_all_cells(padding_bottom=3, padding_left=3, padding_right=3, padding_top=3)

    disenio.append_layout_element(tabla)

    archivo_pdf = f"turnos_cancelados_{anio_actual}_{mes_actual}.pdf"
    PDF.write(what=documento, where_to=archivo_pdf)

    return FileResponse(
        archivo_pdf,
        media_type="application/pdf",
        filename=archivo_pdf
    )
