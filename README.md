Universidad Nacional de Lanús (UNLa)
---
Trabajo Práctico – Gestión de Turnos (API REST)
---
Este proyecto corresponde al Trabajo Práctico de la materia Seminario de Lenguajes – Python (2025).
Consiste en el desarrollo de una API REST para la gestión de turnos y personas, con operaciones ABM y generación de reportes en JSON, PDF y CSV, desarrollados de manera incremental.

---
Equipo docente: 
- Mg. Lic. María Alejandra Vranic
- Lic. Nicolás Borea
- Lic. Gonzalo Cerbelli


Integrantes del grupo 12:
- Francisco Robles 
- Lucio Karabetian
- Morena Rios Carnevale
---
Tecnologias utilizadas:
- Python 
- FastApi
- SQLite
- SQLAlchemy
- Pandas
- Borb
- Uvicorn
---
Ejecución del proyecto:

1. Clonar el repositorio
```bash
git clone https://github.com/usuario/repositorio.git
cd repositorio
```
2. Crear entorno virtual
```bash
python -m venv .venv

# Linux/Mac
source .venv/bin/activate

# Windows    
.venv\Scripts\activate        
```
3. Instalar dependencias
```bash
pip install -r requirements.txt
```
4. Ejecutar la API
```bash
uvicorn main:app --reload
```
5. Acceder a la aplicación
- API base: http://127.0.0.1:8000
- Documentación interactiva (Swagger): http://127.0.0.1:8000/docs
- Documentación alternativa (ReDoc): http://127.0.0.1:8000/redoc
- Colección Postman incluida en el repositorio
---
 Endpoints realizados:


A. ABM de personas
- POST /personas (Francisco Robles)
- GET /personas (Francisco Robles)
- GET /personas/{id} (Francisco Robles)
- PUT /personas/{id} (Lucio Karabetian)
- PATCH /personas/{id} (Francisco Robles)
- DELETE /personas/{id} (Lucio Karabetian)


B. ABM de turnos
- POST /turno (Morena Rios)
- GET /turnos (Morena Rios)
- GET /turno/{id} (Morena Rios)
- PUT /turnos/{id} (Lucio Karabetian)
- DELETE /turnos/{id} (Lucio Karabetian)


C. Cálculo de turnos disponibles
- GET /turnos-disponibles?fecha=YYYY-MM-DD (Morena Rios)


D. Gestión de estado de turno
- PUT /turno/{id}/cancelar (Morena Rios)
- PUT /turno/{id}/confirmar (Morena Rios)
- PATCH /turno/{id}/asistido (Morena Rios)


E. Endpoints de reportes - F. Reportes en PDF - G. Reportes en CSV
- GET /reportes/turnos-por-fecha?fecha=YYYY-MM-DD (Lucio Karabetian)
- GET /reportes/turnos-cancelados-por-mes (Lucio Karabetian)
- GET /reportes/turnos-por-persona?dni=12345678 (Morena Rios)
- GET /reportes/turnos-cancelados?min=5 (Morena Rios)
- GET /reportes/turnos-confirmados?desde=YYYY-MM-DD&hasta=YYYY-MM-DD (Francisco Robles)
- GET /reportes/estado-personas?habilitada=true/false (Francisco Robles)

---
Link al video: https://www.youtube.com/watch?v=AKkC4pTn2dU

Link al postman: https://morenarioscarnevale5-6031694.postman.co/workspace/Morena-Rios-Carnevale's-Workspa~3602c8f9-d514-44c5-8cd2-286ab0adc738/collection/48622647-74cc88ce-894c-4e78-b8ed-f108ce77f1a3?action=share&creator=48622647 
