# 🦷 MuelAI

Asistente de triage odontologico conversacional para pacientes de clinicas dentales, operando sobre WhatsApp y soportado por un panel web administrativo.

MuelAI resuelve un problema operativo comun en clinicas dentales: los pacientes no siempre saben si su dolor o sintoma es una consulta general, una urgencia, o una posible emergencia medica. Cuando no hay atencion 24/7, el tiempo de respuesta se vuelve irregular y se pierde trazabilidad de casos.

La solucion implementa un asistente conversacional que vive en WhatsApp, sin obligar al paciente a instalar apps ni crear cuentas. El mensaje entra por Twilio, se enruta a un webhook FastAPI, y se procesa por un grafo de decisiones LangGraph con estado persistido por paciente.

El sistema clasifica y actua sobre tres categorias de triage: `general` (orientacion y contexto clinico), `urgency` (intento de conexion con doctor y flujo de espera si no hay disponibilidad) y `emergency` (derivacion inmediata a contactos de emergencia). Toda la orquestacion conserva estado por `thread_id = phone`.

Estado actual: MVP funcional end-to-end (webhook, grafo, DB, panel admin basico y tests). Para produccion faltan principalmente hardening operacional: auth/admin robusto, monitoreo, migracion a PostgreSQL para escala, y proceso de numero WhatsApp real fuera de Sandbox.

| Badge      | Estado                                                                                           |
| ---------- | ------------------------------------------------------------------------------------------------ |
| Build      | ![Build](https://img.shields.io/badge/build-passing-brightgreen)                                 |
| Python     | ![Python](https://img.shields.io/badge/python-3.11%2B-blue)                                      |
| Licencia   | ![License](https://img.shields.io/badge/license-MIT-lightgrey)                                   |
| Plataforma | ![Platform](https://img.shields.io/badge/platform-Linux%20%7C%20Mac%20%7C%20Cloud-informational) |

| Canal     | Tecnologia          | Usuarios            |
| --------- | ------------------- | ------------------- |
| WhatsApp  | Twilio Business API | Pacientes           |
| Web Admin | Streamlit           | Odontologos / Staff |

## Tabla De Contenidos

- [1. Header Y Descripcion Ejecutiva](#-muelai)
- [2. Tabla De Contenidos](#tabla-de-contenidos)
- [3. Stack Tecnologico](#3-stack-tecnologico)
- [4. Arquitectura De Alto Nivel](#4-arquitectura-de-alto-nivel)
- [5. Estructura De Carpetas](#5-estructura-de-carpetas)
- [6. Modelo De Datos](#6-modelo-de-datos)
- [7. Estado Conversacional](#7-estado-conversacional)
- [8. Flujo Del Grafo LangGraph](#8-flujo-del-grafo-langgraph)
- [9. Flujos De Actividad](#9-flujos-de-actividad-los-4-escenarios-principales)
- [10. Agentes LLM Y Prompts](#10-agentes-llm-y-prompts)
- [11. Capa API (FastAPI + Twilio)](#11-capa-api-fastapi--twilio)
- [12. Panel Administrativo (Streamlit)](#12-panel-administrativo-streamlit)
- [13. Servicios De Dominio](#13-servicios-de-dominio)
- [14. Setup Y Configuracion Local](#14-setup-y-configuracion-local)
- [15. Variables De Entorno](#15-variables-de-entorno-referencia-completa)
- [16. Testing](#16-testing)
- [17. Deploy En Produccion](#17-deploy-en-produccion)
- [18. Troubleshooting](#18-troubleshooting)
- [19. Roadmap](#19-roadmap)
- [20. Contribuir Al Proyecto](#20-contribuir-al-proyecto)

## 3. Stack Tecnologico

| Capa                        | Tecnologia                  | Rol en el sistema                                            |
| --------------------------- | --------------------------- | ------------------------------------------------------------ |
| Canal de mensajeria         | WhatsApp + Twilio           | Entrada/salida de mensajes del paciente                      |
| API Gateway                 | FastAPI + Uvicorn           | Endpoint webhook, validacion y orquestacion de request       |
| Orquestacion conversacional | LangGraph                   | Flujo por nodos y transiciones condicionales                 |
| LLM                         | Google Gemini via LangChain | Clasificacion semantica y generacion de respuestas           |
| ORM + Persistencia          | SQLAlchemy + SQLite         | Modelado y almacenamiento de pacientes, doctores e historial |
| Panel admin                 | Streamlit                   | Visualizacion operativa y toggles de disponibilidad          |
| Deploy                      | Railway / Render            | Hosting con HTTPS publico para webhook Twilio                |
| Testing                     | pytest + fastapi TestClient | Validacion de rutas, servicios y API sin dependencias reales |

Decisiones de arquitectura: FastAPI permite webhook rapido y simple para Twilio; LangGraph separa logica de decisiones del transporte; Gemini via LangChain simplifica integracion con prompts estructurados; SQLAlchemy aporta capa de dominio limpia para migrar despues a PostgreSQL; Streamlit permite panel operativo de bajo costo para MVP; y pytest/TestClient reduce riesgo de regresiones sin depender de llamadas externas no deterministas.

## 4. Arquitectura De Alto Nivel

```mermaid
flowchart LR
    WA["Paciente en WhatsApp"] --> TW["Twilio WhatsApp API"]
    TW --> API["FastAPI Webhook\nPOST /webhook/twilio"]
    API --> LG["LangGraph Engine\nthread_id = phone"]

    subgraph G["Nodos del grafo"]
      V[verify_patient]
      R[register_patient]
      C[classify_message]
      GQ[handle_general_query]
      U[handle_dental_urgency]
      CA[check_availability]
      CD[connect_doctor]
      E[handle_medical_emergency]
    end

    LG --> G
    G --> AG["Agentes LLM\nClassifier + Responder"]
    G --> DB[(SQLite)]
    DB --> ADM["Streamlit Admin"]
    API --> TW

    style API fill:#0ea5e9,color:#fff
    style LG fill:#4f46e5,color:#fff
    style DB fill:#334155,color:#fff
    style ADM fill:#0f766e,color:#fff
```

Filosofia de diseno:
- Webhook stateless: cada POST se procesa como evento independiente. El servidor no mantiene sesion en memoria por usuario.
- Identidad por `thread_id = phone_number`: unifica sesion conversacional y paciente natural de WhatsApp.
- Eliminacion de `interrupt`: en v2 se reemplazo por estado persistido `awaiting_human`, compatible con modelo asincrono webhook.
- Separacion por capas: API (transporte), graph (orquestacion), agents (LLM), services (dominio), database (persistencia), admin (operacion).

## 5. Estructura De Carpetas

```text
MuelAI/
├── main.py                      # Entrypoint FastAPI, lifespan y health check
├── README.md                    # Documentacion tecnica principal
├── SYSTEM_DESIGN.md             # Documento de diseno base del sistema
├── SYSTEM_DESING_v2.md          # Documento de vision v2 (WhatsApp-first)
├── pyproject.toml               # Metadata Poetry y dependencias base
├── requirements.txt             # Dependencias pip para ejecucion local
├── .env.example                 # Plantilla de variables de entorno
├── src/
│   ├── __init__.py              # Paquete raiz
│   ├── main.py                  # UI Streamlit legacy (fase previa)
│   ├── settings.py              # Settings centralizados (Pydantic)
│   ├── api/
│   │   ├── __init__.py          # Paquete API
│   │   ├── webhook.py           # Router POST /webhook/twilio
│   │   └── twilio_client.py     # Cliente de salida WhatsApp via Twilio
│   ├── admin/
│   │   ├── __init__.py          # Paquete admin
│   │   └── app.py               # Panel Streamlit administrativo
│   ├── graph/
│   │   ├── __init__.py          # Exportes del modulo de grafo
│   │   ├── state.py             # ConversationState
│   │   ├── nodes.py             # Nodos de negocio del flujo
│   │   ├── edges.py             # Routing condicional
│   │   └── graph.py             # Ensamblaje y compilacion del StateGraph
│   ├── agents/
│   │   ├── __init__.py          # Exportes de agentes
│   │   ├── classifier.py        # MessageClassifier (LLM)
│   │   ├── responder.py         # DentalResponder (LLM)
│   │   └── prompts.py           # Prompts del sistema
│   ├── services/
│   │   ├── __init__.py          # Exportes de servicios
│   │   ├── patient_service.py   # Logica de pacientes e historial
│   │   └── doctor_service.py    # Logica de disponibilidad/asignacion de doctor
│   ├── database/
│   │   ├── __init__.py          # Exportes DB
│   │   ├── models.py            # Modelos SQLAlchemy
│   │   └── connection.py        # Engine/session/init/seed
│   └── schemas/
│       ├── __init__.py          # Exportes Pydantic
│       └── models.py            # DTOs y esquemas de entrada/salida
└── tests/
    ├── __init__.py              # Paquete tests
    ├── test_graph.py            # Tests de rutas y compilacion LangGraph
    ├── test_webhook.py          # Tests API/webhook con mocks
    └── test_services.py         # Tests servicios con SQLite in-memory
```

| Modulo         | Responsabilidad principal                                  |
| -------------- | ---------------------------------------------------------- |
| `src/api`      | Integracion Twilio/FastAPI para entrada/salida de mensajes |
| `src/graph`    | Estado conversacional y flujo de decision                  |
| `src/agents`   | Clasificacion y generacion de respuestas con Gemini        |
| `src/services` | Reglas de negocio para pacientes y doctores                |
| `src/database` | Persistencia ORM y gestion de sesiones                     |
| `src/schemas`  | Contratos de datos (Pydantic)                              |
| `src/admin`    | Operacion manual de disponibilidad y consulta basica       |

## 6. Modelo De Datos

### 6.1 Diagrama ER

```mermaid
erDiagram
    PATIENT ||--o{ MEDICAL_HISTORY : has

    PATIENT {
      int id PK
      string name NOT_NULL
      string phone UNIQUE_NOT_NULL
      string email UNIQUE_NULLABLE
      datetime created_at NOT_NULL
    }

    MEDICAL_HISTORY {
      int id PK
      int patient_id FK_NOT_NULL
      datetime date NOT_NULL
      string diagnosis NOT_NULL
      text treatment NOT_NULL
      text notes NULLABLE
    }

    DOCTOR {
      int id PK
      string name NOT_NULL
      string specialty NOT_NULL
      string phone NOT_NULL
      bool is_available NOT_NULL
      string current_chat_id NULLABLE
    }
```

### 6.2 Entidades y campos

#### Patient

| Campo        | Tipo          | Constraint                 | Descripcion funcional              |
| ------------ | ------------- | -------------------------- | ---------------------------------- |
| `id`         | `Integer`     | PK, autoincrement          | Identificador interno              |
| `name`       | `String(100)` | NOT NULL                   | Nombre del paciente                |
| `phone`      | `String(20)`  | UNIQUE, NOT NULL           | Identidad del paciente en WhatsApp |
| `email`      | `String(100)` | UNIQUE, NULLABLE           | Contacto opcional                  |
| `created_at` | `DateTime`    | NOT NULL, default `utcnow` | Fecha de alta                      |

#### MedicalHistory

| Campo        | Tipo          | Constraint                 | Descripcion funcional      |
| ------------ | ------------- | -------------------------- | -------------------------- |
| `id`         | `Integer`     | PK, autoincrement          | Identificador de registro  |
| `patient_id` | `Integer`     | FK `patients.id`, NOT NULL | Paciente asociado          |
| `date`       | `DateTime`    | NOT NULL, default `utcnow` | Fecha del registro         |
| `diagnosis`  | `String(200)` | NOT NULL                   | Diagnostico registrado     |
| `treatment`  | `Text`        | NOT NULL                   | Tratamiento realizado      |
| `notes`      | `Text`        | NULLABLE                   | Notas clinicas adicionales |

#### Doctor

| Campo             | Tipo          | Constraint                | Descripcion funcional          |
| ----------------- | ------------- | ------------------------- | ------------------------------ |
| `id`              | `Integer`     | PK, autoincrement         | Identificador de doctor        |
| `name`            | `String(100)` | NOT NULL                  | Nombre del profesional         |
| `specialty`       | `String(100)` | NOT NULL                  | Especialidad odontologica      |
| `phone`           | `String(20)`  | NOT NULL                  | Contacto del doctor            |
| `is_available`    | `Boolean`     | NOT NULL, default `False` | Disponibilidad para asignacion |
| `current_chat_id` | `String(100)` | NULLABLE                  | Identificador del chat activo  |

### 6.3 Decisiones de diseno del modelo

- `phone` como identificador natural del paciente: es el dato estable entregado por WhatsApp/Twilio, evitando logins y IDs externos.
- `current_chat_id` en `Doctor`: permite marcar una ocupacion operativa por conversacion.
- SQLite para MVP: minimo costo operativo, setup inmediato y buen fit para prototipado local. Migrar a PostgreSQL requiere actualizar `DATABASE_URL` y driver, manteniendo el modelo ORM.

### 6.4 Normalizacion de telefono

Proceso critico para consistencia de estado:

```text
"whatsapp:+51987654321" -> "+51987654321"
```

Si no se normaliza, el mismo paciente podria abrir multiples hilos (`whatsapp:+51...` vs `+51...`) y romper la persistencia conversacional por `thread_id`.

## 7. Estado Conversacional

### 7.1 ConversationState (actual)

```python
class ConversationState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]
    patient_phone: Optional[str]
    patient_id: Optional[int]
    patient_exists: bool
    patient_name: Optional[str]
    classification: Optional[Literal["general", "urgency", "emergency"]]
    medical_history: Optional[str]
    awaiting_human: bool
    available_doctors: list[dict]
    assigned_doctor: Optional[dict]
    emergency_contacts_provided: bool
```

### 7.2 Tabla de campos del estado

| Campo                         | Tipo                | Valor inicial              | Rol en el flujo                          |
| ----------------------------- | ------------------- | -------------------------- | ---------------------------------------- |
| `messages`                    | `list[BaseMessage]` | `[]`                       | Historial conversacional para nodos/LLM  |
| `patient_phone`               | `Optional[str]`     | `patient_phone` de entrada | Identidad y `thread_id`                  |
| `patient_id`                  | `Optional[int]`     | `None`                     | Vinculo con DB                           |
| `patient_exists`              | `bool`              | `False`                    | Decide registro o flujo normal           |
| `patient_name`                | `Optional[str]`     | `None`                     | Personalizacion de respuestas            |
| `classification`              | `Optional[str]`     | `None`                     | Ruta `general/urgency/emergency`         |
| `medical_history`             | `Optional[str]`     | `None`                     | Contexto clinico en consultas generales  |
| `awaiting_human`              | `bool`              | `False`                    | Flag de espera por disponibilidad humana |
| `available_doctors`           | `list[dict]`        | `[]`                       | Resultado de consulta de disponibilidad  |
| `assigned_doctor`             | `Optional[dict]`    | `None`                     | Doctor elegido para el caso              |
| `emergency_contacts_provided` | `bool`              | `False`                    | Marca de respuesta de emergencia emitida |

### 7.3 Ciclo de vida del estado

- Primer mensaje: el webhook crea estado base con `messages=[HumanMessage]` y `patient_phone`.
- Invocaciones siguientes: LangGraph recupera estado previo via `checkpointer=MemorySaver` usando el mismo `thread_id=phone`.
- La continuidad por numero evita mezclar conversaciones entre pacientes.
- Diferencia clave primera vs posteriores: en primera puede ejecutar `register_patient`; en posteriores reutiliza `patient_exists`, `awaiting_human` y resto de campos persistidos.

### 7.4 Campo `awaiting_human` (profundo)

- Se setea en `True` en `handle_dental_urgency` cuando no hay doctores disponibles.
- Se setea en `False` en `check_doctor_availability` cuando ya existe disponibilidad.
- Con `awaiting_human=True`, el flujo se desvía a `check_availability` para reintento en mensajes posteriores, sin reclasificar como si fuera un caso nuevo.
- Este flag reemplaza el `interrupt` de versiones anteriores, permitiendo arquitectura webhook stateless.

## 8. Flujo Del Grafo LangGraph

### 8.1 Diagrama completo

```mermaid
flowchart TD
    START([START]):::entry --> VP[verify_patient]:::entry

    VP -->|register_patient| RP[register_patient]:::decision
    VP -->|check_availability| CA[check_availability]:::decision
    VP -->|classify_message| PPF[post_patient_flow]:::decision

    PPF -->|check_availability| CA
    PPF -->|classify_message| CM[classify_message]:::decision

    RP -->|check_availability| CA
    RP -->|classify_message| CM

    CM -->|general| HGQ[handle_general_query]:::response
    CM -->|urgency| HDU[handle_dental_urgency]:::response
    CM -->|emergency| HME[handle_medical_emergency]:::response

    HDU -->|connect_doctor| CD[connect_doctor]:::response
    HDU -->|still_waiting| END1([END]):::terminal

    CA -->|connect_doctor| CD
    CA -->|still_waiting| END2([END]):::terminal

    HGQ --> END3([END]):::terminal
    HME --> END4([END]):::terminal
    CD --> END5([END]):::terminal

    classDef entry fill:#0ea5e9,color:#fff
    classDef decision fill:#f59e0b,color:#111
    classDef response fill:#10b981,color:#fff
    classDef terminal fill:#334155,color:#fff
```

### 8.2 Tabla de nodos

| Nodo                       | Archivo              | Inputs del estado                               | Outputs al estado                                                    | Cuando se ejecuta         |
| -------------------------- | -------------------- | ----------------------------------------------- | -------------------------------------------------------------------- | ------------------------- |
| `verify_patient`           | `src/graph/nodes.py` | `patient_phone`                                 | `patient_exists`, `patient_id`, `patient_name`                       | Entrada del flujo         |
| `register_patient`         | `src/graph/nodes.py` | `patient_phone`, `messages`                     | registro + `patient_*`, `messages`                                   | Paciente no existente     |
| `classify_message`         | `src/graph/nodes.py` | `messages`                                      | `classification`                                                     | Ruta normal sin espera    |
| `handle_general_query`     | `src/graph/nodes.py` | `classification`, `patient_id`, `messages`      | `medical_history`, `messages`                                        | Clasificacion `general`   |
| `handle_dental_urgency`    | `src/graph/nodes.py` | `classification`, `messages`, `patient_name`    | `available_doctors`, `awaiting_human`, `messages`                    | Clasificacion `urgency`   |
| `check_availability`       | `src/graph/nodes.py` | `awaiting_human`, `patient_name`, `messages`    | `available_doctors`, `assigned_doctor`, `awaiting_human`, `messages` | Reintento por espera      |
| `connect_doctor`           | `src/graph/nodes.py` | `available_doctors`, `patient_name`, `messages` | `assigned_doctor`, `messages`                                        | Hay doctor disponible     |
| `handle_medical_emergency` | `src/graph/nodes.py` | `classification`, `messages`, `patient_name`    | `emergency_contacts_provided`, `messages`                            | Clasificacion `emergency` |

### 8.3 Routing condicional

| Funcion                      | Valores posibles de retorno                                                   | Criterio                                |
| ---------------------------- | ----------------------------------------------------------------------------- | --------------------------------------- |
| `route_after_patient_check`  | `register_patient` / `classify_message` / `check_availability`                | paciente existe + flag `awaiting_human` |
| `route_after_patient_flow`   | `check_availability` / `classify_message`                                     | bypass por `awaiting_human`             |
| `route_after_classification` | `handle_general_query` / `handle_dental_urgency` / `handle_medical_emergency` | valor `classification`                  |
| `route_after_urgency`        | `connect_doctor` / `still_waiting`                                            | lista de doctores disponibles           |
| `route_after_urgency_check`  | `connect_doctor` / `still_waiting`                                            | lista de doctores disponibles           |

### 8.4 Nodos (detalle)

#### verify_patient
- Busca paciente por telefono en DB.
- Lee: `patient_phone`.
- Escribe: `patient_exists`, `patient_id`, `patient_name`.
- Edge cases: telefono vacio deja paciente no identificado.

#### register_patient
- Crea paciente nuevo con nombre temporal basado en telefono.
- Lee: `patient_phone`, `messages`.
- Escribe: `patient_exists=True`, `patient_id`, `patient_name`, `messages`.
- Edge cases: sin telefono agrega mensaje de requerimiento.

#### classify_message
- Toma ultimo `HumanMessage` y clasifica con LLM.
- Lee: `messages`.
- Escribe: `classification`.
- Edge cases: sin mensaje humano cae a `general`.

#### handle_general_query
- Carga historial medico y genera respuesta contextual.
- Lee: `patient_id`, `patient_name`, `messages`.
- Escribe: `medical_history`, `messages`.
- Edge cases: paciente sin historial retorna texto por defecto.

#### handle_dental_urgency
- Consulta disponibilidad y responde urgencia.
- Lee: `patient_name`, `messages`.
- Escribe: `available_doctors`, `awaiting_human`, `assigned_doctor`, `messages`.
- Edge cases: sin doctores deja `awaiting_human=True` y mensaje de espera.

#### check_availability
- Reconsulta disponibilidad para casos en espera.
- Lee: `patient_name`, `messages`.
- Escribe: `available_doctors`, `assigned_doctor`, `awaiting_human`, `messages`.
- Edge cases: si sigue sin disponibilidad mantiene espera y agrega mensaje.

#### connect_doctor
- Toma primer doctor disponible y confirma conexion al paciente.
- Lee: `available_doctors`, `patient_name`, `messages`.
- Escribe: `assigned_doctor`, `messages`.
- Edge cases: lista vacia responde fallback de espera.

#### handle_medical_emergency
- Prioriza derivacion y contactos de emergencia.
- Lee: `patient_name`, `messages`.
- Escribe: `emergency_contacts_provided=True`, `messages`.
- Edge cases: siempre finaliza flujo con respuesta critica.

## 9. Flujos De Actividad (los 4 escenarios principales)

### Escenario A - Consulta general, paciente existente

```mermaid
sequenceDiagram
    participant P as Paciente
    participant T as Twilio
    participant F as FastAPI
    participant G as LangGraph
    participant D as SQLite
    participant L as Gemini

    P->>T: "que antibioticos puedo tomar para una infeccion?"
    T->>F: POST /webhook/twilio
    F->>G: invoke(thread_id=+51987654321)
    G->>D: verify_patient
    D-->>G: paciente existente
    G->>L: classify_message
    L-->>G: general
    G->>D: get_medical_history_summary
    G->>L: respond_general_query
    L-->>G: respuesta contextual
    G-->>F: AIMessage
    F->>T: send_whatsapp_message
    T-->>P: respuesta
```

Flujo normal de bajo riesgo: identifica paciente, clasifica `general`, trae historial y responde orientacion.

### Escenario B - Paciente nuevo + consulta general

```mermaid
sequenceDiagram
    participant P as Paciente
    participant T as Twilio
    participant F as FastAPI
    participant G as LangGraph
    participant D as SQLite

    P->>T: "hola, quiero una cita"
    T->>F: POST webhook
    F->>G: invoke(thread_id=+51987654321)
    G->>D: verify_patient
    D-->>G: no existe
    G->>D: register_patient
    G->>G: classify_message
    G-->>F: mensaje de bienvenida + orientacion
    F->>T: send_message
    T-->>P: respuesta
```

Antes de clasificar, el sistema registra paciente con nombre temporal y continua flujo.

### Escenario C - Urgencia dental con doctor disponible

```mermaid
sequenceDiagram
    participant P as Paciente
    participant T as Twilio
    participant F as FastAPI
    participant G as LangGraph
    participant D as SQLite
    participant L as Gemini

    P->>T: "tengo dolor insoportable"
    T->>F: POST webhook
    F->>G: invoke(phone)
    G->>L: classify -> urgency
    G->>D: get_available_doctors
    D-->>G: lista con doctor
    G->>L: respond_urgency(contexto doctores)
    G->>G: connect_doctor
    G-->>F: AIMessage asignando doctor
    F->>T: send_message
    T-->>P: confirmacion
```

Cuando hay disponibilidad, la urgencia se resuelve en la misma invocacion sin pasar a espera.

### Escenario D - Urgencia sin doctor disponible (flujo clave)

```mermaid
sequenceDiagram
    participant P as Paciente
    participant T as Twilio
    participant F as FastAPI
    participant G as LangGraph
    participant D as SQLite
    participant A as Admin Streamlit

    P->>T: "tengo dolor insoportable en una muela"
    T->>F: POST webhook
    F->>G: invoke(thread_id=+51987654321)
    G->>D: get_available_doctors
    D-->>G: []
    G->>G: awaiting_human=True
    G-->>F: "seguimos buscando doctor"
    F->>T: send_message
    T-->>P: mensaje de espera

    A->>D: toggle doctor is_available=True

    P->>T: "hay alguna novedad?"
    T->>F: POST webhook
    F->>G: invoke(thread_id=+51987654321)
    G->>G: route_after_patient_check -> check_availability
    G->>D: get_available_doctors
    D-->>G: [doctor]
    G->>G: awaiting_human=False + assigned_doctor
    G->>G: connect_doctor
    G-->>F: mensaje de asignacion
    F->>T: send_message
    T-->>P: confirmacion de doctor
```

Este flujo reemplaza el antiguo `interrupt` por reintentos stateless basados en estado persistido.

### Escenario E - Emergencia medica

```mermaid
sequenceDiagram
    participant P as Paciente
    participant T as Twilio
    participant F as FastAPI
    participant G as LangGraph
    participant L as Gemini

    P->>T: "me golpee la mandibula y hay mucha sangre"
    T->>F: POST webhook
    F->>G: invoke(phone)
    G->>L: classify -> emergency
    G->>L: respond_emergency
    G-->>F: contactos de emergencia
    F->>T: send_message
    T-->>P: derivacion inmediata
```

No intenta agenda ni asignacion de doctor: prioriza seguridad y deriva a servicios de emergencia.

## 10. Agentes LLM Y Prompts

### 10.1 Tabla de agentes

| Agente       | Clase               | Modelo                                               | Temperatura | Proposito                              |
| ------------ | ------------------- | ---------------------------------------------------- | ----------- | -------------------------------------- |
| Clasificador | `MessageClassifier` | `settings.gemini_model` (default `gemini-2.5-flash`) | `0.0`       | Determinar `general/urgency/emergency` |
| Respondedor  | `DentalResponder`   | `settings.gemini_model`                              | `0.7`       | Respuesta contextual por tipo de caso  |

### 10.2 MessageClassifier

- Usa temperatura `0.0` para minimizar variabilidad y maximizar consistencia de labels.
- Input: `SystemMessage(CLASSIFIER_SYSTEM_PROMPT)` + `HumanMessage(mensaje)`.
- Output esperado estricto: `general`, `urgency`, `emergency`.
- Fallback defensivo: cualquier salida fuera de ese set retorna `general`.

Ejemplos esperados:
- `"cuanto cuesta una limpieza?"` -> `general`
- `"me duele muchisimo una muela desde ayer"` -> `urgency`
- `"se me cayo un diente y hay mucha sangre"` -> `emergency`

### 10.3 DentalResponder

- Usa temperatura `0.7` para respuestas mas naturales y empaticas.
- `respond_general_query`: recibe mensaje, historial medico, nombre y ultimos mensajes.
- `respond_urgency`: recibe mensaje, lista de doctores disponibles y nombre.
- `respond_emergency`: recibe mensaje y nombre, agregando contexto de contactos de emergencia.

Construccion de contexto: en consultas generales se inyecta bloque de historial (`PatientService.get_medical_history_summary`) antes de invocar LLM.

### 10.4 Filosofia de prompts

- Prompts centralizados en `src/agents/prompts.py` separan contenido de negocio de logica procedural.
- Ajustar tono/reglas no requiere cambios en `nodes.py` o `graph.py`.
- Idioma: prompts estan en espanol, con tono empatico, claro y sin sobrediagnostico.

## 11. Capa API (FastAPI + Twilio)

### 11.1 Diagrama del webhook

```mermaid
flowchart LR
    T[Twilio POST Form] --> V[Validar campos From/Body]
    V --> N[normalize_phone]
    N --> S[Construir estado inicial]
    S --> G[graph.invoke(thread_id=phone)]
    G --> X[Extraer ultimo AIMessage]
    X --> W[TwilioClient.send_whatsapp_message]
    W --> R[HTTP 200 body vacio]
```

### 11.2 Endpoint

- Metodo: `POST /webhook/twilio`
- Content-Type: `application/x-www-form-urlencoded`
- Campos esperados:

| Campo        | Requerido | Descripcion                                  |
| ------------ | --------- | -------------------------------------------- |
| `From`       | Si        | Numero origen, p.ej. `whatsapp:+51987654321` |
| `Body`       | Si        | Texto del paciente                           |
| `To`         | No        | Numero destino Twilio                        |
| `MessageSid` | No        | ID del mensaje                               |
| `AccountSid` | No        | ID de cuenta Twilio                          |

- Respuesta: `200 OK` con body vacio.
- Razon: la respuesta al paciente se envia por API de Twilio (mensaje saliente), no por TwiML de retorno.

### 11.3 Normalizacion de telefono

```python
def normalize_phone(raw: str) -> str:
    if raw.startswith("whatsapp:"):
        return raw.split("whatsapp:", 1)[1].strip()
    return raw.strip()
```

Casos:
- `whatsapp:+51987654321` -> `+51987654321`
- `+51987654321` -> `+51987654321`

### 11.4 Inicializacion del grafo

En `src/api/webhook.py`:
- `_graph = build_graph()` a nivel modulo.
- Se instancia una sola vez por proceso.

Motivo: evitar recompilar grafo por request (overhead) y mantener continuidad por checkpointer/thread.

### 11.5 TwilioClient

- Autenticacion: `Client(settings.twilio_account_sid, settings.twilio_auth_token)`.
- `from_`: `settings.twilio_phone_number` (incluye `whatsapp:`).
- `to`: el webhook normaliza a `+...` y cliente lo transforma en `whatsapp:+...`.
- Manejo de errores: captura `TwilioRestException` y `Exception`, loguea y no relanza para no romper el webhook.

### 11.6 Health check

`GET /` devuelve:

```json
{"status": "ok", "service": "MuelAI"}
```

Util para probes de disponibilidad en Railway/Render y monitoreo basico.

## 12. Panel Administrativo (Streamlit)

### 12.1 Proposito

- Permite al staff revisar disponibilidad de doctores y consultar pacientes demo.
- No reemplaza un CRM ni maneja chat en tiempo real paciente-doctor.
- Corre en puerto separado (`8501`) para desacoplar operacion interna del webhook (`8000`).

### 12.2 Secciones de UI

Requisito funcional objetivo del proyecto:
- Sidebar: disponibilidad de doctores con toggle.
- Tab `Pacientes`: lista/busqueda e historial al seleccionar.
- Tab `En espera`: pacientes con `awaiting_human=True` (auto-refresh).
- Tab `Historial`: vista de registros clinicos por paciente.

Estado actual en codigo (`src/admin/app.py`):
- Implementado: tab `Doctores` + tab `Pacientes`.
- Aun no implementado en ese archivo: tabs `En espera` y `Historial` avanzadas.

### 12.3 Flujo de trabajo admin ante urgencia

```mermaid
flowchart TD
    A[Admin abre panel] --> B[Revisa casos en espera]
    B --> C[Identifica urgencia]
    C --> D[Toggle doctor disponible]
    D --> E[Paciente envia nuevo mensaje]
    E --> F[check_availability en grafo]
    F --> G[connect_doctor]
    G --> H[Paciente recibe asignacion]
```

### 12.4 Consideraciones tecnicas

- Objetivo recomendado: usar `st.cache_data(ttl=30)` para lecturas frecuentes de panel.
- `st.rerun()` tras toggle ya se usa para reflejar cambios inmediatamente.
- Admin y webhook apuntan al mismo `DATABASE_URL`, compartiendo estado de disponibilidad.

## 13. Servicios De Dominio

### 13.1 PatientService

| Metodo                        | Signatura                            | Descripcion                           | Retorno             |
| ----------------------------- | ------------------------------------ | ------------------------------------- | ------------------- |
| `get_patient_by_phone`        | `(session, phone)`                   | Busca paciente por telefono           | `Optional[Patient]` |
| `get_patient_by_email`        | `(session, email)`                   | Busca por email                       | `Optional[Patient]` |
| `get_patient_with_history`    | `(session, patient_id)`              | Carga paciente con relacion historial | `Optional[Patient]` |
| `create_patient`              | `(session, name, phone, email=None)` | Crea paciente y hace `flush`          | `Patient`           |
| `get_medical_history_summary` | `(session, patient_id)`              | Resume historial en texto             | `str`               |
| `patient_exists`              | `(session, phone)`                   | Check booleano de existencia          | `bool`              |

### 13.2 DoctorService

| Metodo                    | Descripcion            | Efecto DB                                   |
| ------------------------- | ---------------------- | ------------------------------------------- |
| `get_available_doctors`   | Lista DTOs disponibles | Lectura                                     |
| `get_all_doctors`         | Lista todos DTOs       | Lectura                                     |
| `set_doctor_availability` | Cambia disponibilidad  | `is_available`                              |
| `assign_doctor_to_chat`   | Asigna doctor a chat   | `current_chat_id`, `is_available=False`     |
| `release_doctor`          | Libera doctor          | `current_chat_id=None`, `is_available=True` |
| `get_doctor_by_id`        | Busca doctor           | Lectura                                     |

`DoctorAvailability` DTO existe para desacoplar salida de servicio de entidades ORM directas.

### 13.3 Patron de sesion DB

`get_session()` en `src/database/connection.py`:
- Abre sesion SQLAlchemy.
- `yield` para operar.
- `commit` automatico si todo sale bien.
- `rollback` en excepcion.
- `close` siempre.

Esto evita transacciones huérfanas y centraliza manejo transaccional.

## 14. Setup Y Configuracion Local

### 14.1 Requisitos previos

- Python 3.11+ (`python --version`)
- Google AI Studio (Gemini API key): https://aistudio.google.com/
- Twilio: https://www.twilio.com/
- ngrok: https://ngrok.com/download
- Git

### 14.2 Clonar e instalar

```bash
git clone <repo>
cd MuelAI
python -m venv venv
source venv/bin/activate   # Linux/Mac
# venv\Scripts\activate    # Windows
pip install -r requirements.txt
```

### 14.3 Configurar variables

```bash
cp .env.example .env
```

| Variable              | Donde obtenerla                          | Requerida |
| --------------------- | ---------------------------------------- | --------- |
| `GOOGLE_API_KEY`      | Google AI Studio                         | Si        |
| `TWILIO_ACCOUNT_SID`  | Twilio Dashboard                         | Si        |
| `TWILIO_AUTH_TOKEN`   | Twilio Dashboard                         | Si        |
| `TWILIO_PHONE_NUMBER` | Sandbox Twilio (`whatsapp:+14155238886`) | Si        |
| `DATABASE_URL`        | Local default sqlite                     | No        |

### 14.4 Obtener Gemini API Key

1. Ir a `aistudio.google.com`.
2. Iniciar sesion con cuenta Google.
3. Click en `Get API key` -> `Create API key`.
4. Copiar valor a `GOOGLE_API_KEY` en `.env`.

### 14.5 Configurar Twilio Sandbox

1. Crear cuenta en Twilio.
2. Abrir Console -> Messaging -> Try it out -> Send a WhatsApp message.
3. Activar Sandbox enviando el codigo de union al numero de Sandbox desde tu WhatsApp.
4. Copiar `Account SID` y `Auth Token` del Dashboard.
5. Usar `TWILIO_PHONE_NUMBER=whatsapp:+14155238886` (Sandbox).

### 14.6 Inicializar DB

```bash
python -c "from src.database.connection import init_db, seed_demo_data; init_db(); seed_demo_data()"
```

Seed crea:
- 2 pacientes demo
- 3 registros de historial
- 3 doctores con disponibilidad mixta

### 14.7 Correr servidor

```bash
uvicorn main:app --reload --port 8000
```

Verificacion:

```bash
curl http://localhost:8000/
```

Debe responder `{"status":"ok","service":"MuelAI"}`.

### 14.8 Exponer con ngrok

```bash
ngrok http 8000
```

Ejemplo URL: `https://abc123.ngrok.io`

### 14.9 Configurar webhook en Twilio

1. Twilio Console -> Messaging -> Try it out -> Send a WhatsApp message.
2. En Sandbox Settings, configurar:
   - `https://abc123.ngrok.io/webhook/twilio`
3. Metodo HTTP: `POST`.
4. Guardar.

### 14.10 Correr panel admin (opcional)

```bash
streamlit run src/admin/app.py
```

Abrir `http://localhost:8501`.

### 14.11 Probar flujo completo

- Enviar `Hola` al numero Sandbox desde WhatsApp.
- Verificar logs de uvicorn (POST recibido).
- Confirmar respuesta automatica al paciente.

## 15. Variables De Entorno (referencia completa)

### .env.example anotado

```dotenv
# API key de Gemini usada por MessageClassifier y DentalResponder
GOOGLE_API_KEY=

# Credenciales de cuenta Twilio
TWILIO_ACCOUNT_SID=ACXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
TWILIO_AUTH_TOKEN=your_twilio_auth_token

# Numero emisor de WhatsApp (incluye prefijo whatsapp:)
TWILIO_PHONE_NUMBER=whatsapp:+14155238886

# URL SQLAlchemy; por defecto SQLite local para MVP
DATABASE_URL=sqlite:///./dental_clinic.db
```

### Tabla de referencia

| Variable              | Tipo  | Default                        | Descripcion                    |
| --------------------- | ----- | ------------------------------ | ------------------------------ |
| `GOOGLE_API_KEY`      | `str` | none                           | Credencial de Gemini           |
| `TWILIO_ACCOUNT_SID`  | `str` | none                           | Identificador de cuenta Twilio |
| `TWILIO_AUTH_TOKEN`   | `str` | none                           | Token secreto de Twilio        |
| `TWILIO_PHONE_NUMBER` | `str` | none                           | Remitente WhatsApp de Twilio   |
| `DATABASE_URL`        | `str` | `sqlite:///./dental_clinic.db` | Conexion a DB para ORM         |

## 16. Testing

### 16.1 Comandos

```bash
pytest tests/ -v
pytest tests/ -v --tb=short
pytest tests/test_graph.py
pytest tests/test_webhook.py
pytest tests/test_services.py
```

### 16.2 Tabla de tests existentes

| Archivo                  | Test                                        | Que verifica                                           |
| ------------------------ | ------------------------------------------- | ------------------------------------------------------ |
| `tests/test_graph.py`    | `test_initial_state_structure`              | Estructura y defaults del estado inicial               |
| `tests/test_graph.py`    | `test_route_after_patient_check_existing`   | Routing paciente existente                             |
| `tests/test_graph.py`    | `test_route_after_patient_check_new`        | Routing paciente nuevo                                 |
| `tests/test_graph.py`    | `test_route_after_classification_general`   | Ruta `general`                                         |
| `tests/test_graph.py`    | `test_route_after_classification_urgency`   | Ruta `urgency`                                         |
| `tests/test_graph.py`    | `test_route_after_classification_emergency` | Ruta `emergency`                                       |
| `tests/test_graph.py`    | `test_awaiting_human_flow`                  | Bypass a `check_availability` si `awaiting_human=True` |
| `tests/test_graph.py`    | `test_route_after_urgency_keys`             | Claves validas de `route_after_urgency`                |
| `tests/test_graph.py`    | `test_route_after_urgency_check_keys`       | Claves validas de `route_after_urgency_check`          |
| `tests/test_graph.py`    | `test_graph_compiles`                       | Compilacion de `build_graph()` y nodos esperados       |
| `tests/test_webhook.py`  | `test_health_check`                         | `GET /` correcto                                       |
| `tests/test_webhook.py`  | `test_normalize_phone`                      | Normalizacion de numeros                               |
| `tests/test_webhook.py`  | `test_webhook_missing_body`                 | Validacion 422 por falta de form fields                |
| `tests/test_webhook.py`  | `test_webhook_uses_graph_and_twilio_mocks`  | Llamadas a grafo y Twilio mockeadas                    |
| `tests/test_services.py` | `test_patient_service_create_and_find`      | Alta y busqueda de paciente                            |
| `tests/test_services.py` | `test_doctor_service_availability_toggle`   | Cambio de disponibilidad                               |
| `tests/test_services.py` | `test_doctor_service_assign_and_release`    | Asignar/liberar doctor                                 |

### 16.3 Cobertura

```bash
pip install pytest-cov
pytest tests/ --cov=src --cov-report=term-missing
```

Cubierto:
- rutas de grafo y compilacion
- webhook/normalizacion/health
- servicios de dominio con DB in-memory

No cubierto completamente:
- llamadas LLM reales
- Twilio real
- E2E completo WhatsApp (infra externa)

### 16.4 Tests no existentes y por que

- LLM real: costoso y no determinista.
- Twilio real: depende de credenciales/costos/entorno.
- E2E WhatsApp: requiere infraestructura externa y numero activo.

## 17. Deploy En Produccion

### 17.1 Requisitos

- HTTPS publico obligatorio para webhook Twilio.
- Persistencia de DB (volumen o PostgreSQL).
- Variables de entorno en plataforma.

### 17.2 Deploy en Railway (MVP)

1. Crear cuenta en `railway.app`.
2. `New Project` -> `Deploy from GitHub`.
3. Cargar variables de entorno.
4. Start command:

```bash
uvicorn main:app --host 0.0.0.0 --port $PORT
```

5. Obtener URL HTTPS de Railway.
6. Actualizar webhook Twilio a `<url>/webhook/twilio`.
7. Si SQLite persiste en volumen, apuntar `DATABASE_URL` al path montado.

### 17.3 Deploy en Render

Pasos equivalentes:
1. Crear `Web Service` desde repo.
2. Runtime Python.
3. Start command igual a uvicorn.
4. Definir env vars.
5. URL HTTPS de Render al webhook Twilio.

### 17.4 Migracion a numero WhatsApp real

- Sandbox: pruebas limitadas, numero compartido.
- Produccion: numero aprobado por Meta/Twilio.
- Requiere proceso de aprobacion y consideracion de costos por conversacion.
- Cambiar `TWILIO_PHONE_NUMBER` al numero productivo.

### 17.5 Migracion a PostgreSQL

```bash
pip install psycopg2-binary
```

```dotenv
DATABASE_URL=postgresql://user:password@host:5432/muelai
```

SQLAlchemy permite migracion con impacto acotado en codigo de dominio.

## 18. Troubleshooting

| Sintoma                                 | Causa probable                           | Solucion                                                     |
| --------------------------------------- | ---------------------------------------- | ------------------------------------------------------------ |
| Bot no responde en WhatsApp             | Webhook mal configurado                  | Verificar URL publica + ruta `/webhook/twilio` + metodo POST |
| Error 401 Twilio                        | Auth token invalido                      | Re-copiar `TWILIO_AUTH_TOKEN` del dashboard                  |
| `API key invalid`                       | API key Gemini incorrecta                | Validar `GOOGLE_API_KEY` y reiniciar proceso                 |
| Clasifica todo como `general`           | Prompt/salida no valida del clasificador | Verificar `temperature=0.0` y prompt de clasificacion        |
| Estado no persiste                      | `thread_id` inconsistente                | Confirmar `thread_id=phone` normalizado                      |
| ngrok cambia URL                        | Plan free de ngrok                       | Reconfigurar webhook en Twilio al reiniciar ngrok            |
| `database is locked`                    | Contencion SQLite                        | Reducir concurrencia o migrar a PostgreSQL                   |
| Panel admin no refleja cambio inmediato | Estado UI sin rerun/cache                | Usar toggle + `st.rerun()` y revisar TTL de cache            |

## 19. Roadmap

```mermaid
gantt
    title Roadmap MuelAI
    dateFormat  YYYY-MM-DD

    section Fase 1 - MVP Local (completado)
    Fix grafo sin interrupt          :done, f1a, 2026-01-01, 4d
    Webhook FastAPI + Twilio Sandbox:done, f1b, after f1a, 4d
    Normalizacion de phone          :done, f1c, after f1b, 2d
    Tests basicos                   :done, f1d, after f1c, 3d

    section Fase 2 - Deploy (en progreso)
    Deploy Railway/Render           :active, f2a, after f1d, 5d
    Numero WhatsApp real            :f2b, after f2a, 7d
    Panel Admin Streamlit           :f2c, after f2a, 5d
    Logging/monitoring basico       :f2d, after f2a, 3d

    section Fase 3 - Producto (proximo)
    Agendamiento de citas           :f3a, after f2b, 6d
    Recordatorios proactivos        :f3b, after f3a, 5d
    Migracion PostgreSQL            :f3c, after f3a, 4d
    Auth panel admin                :f3d, after f3a, 4d

    section Fase 4 - Escala (futuro)
    Canal web paralelo              :f4a, after f3d, 8d
    Multi-clinica                   :f4b, after f4a, 10d
    Integracion con sistemas dentales:f4c, after f4b, 12d
    Analytics de conversaciones     :f4d, after f4b, 8d
```

## 20. Contribuir Al Proyecto

### 20.1 Convenciones de codigo

- PEP 8.
- Type hints en funciones publicas.
- Docstrings en servicios/agentes y logica no trivial.
- Toda funcionalidad nueva debe incluir tests antes de merge.

### 20.2 Agregar un nodo al grafo

1. Crear funcion en `src/graph/nodes.py`:

```python
def nuevo_nodo(state: ConversationState) -> dict:
    ...
```

2. Si necesita decision condicional, crear routing en `src/graph/edges.py`.
3. Registrar nodo en `src/graph/graph.py` con `graph.add_node()`.
4. Conectar transiciones con `add_edge` o `add_conditional_edges`.
5. Agregar tests en `tests/test_graph.py` para nodos y claves de routing.

### 20.3 Modificar prompts

Editar `src/agents/prompts.py`.
No requiere tocar nodos/servicios si solo cambias instrucciones de LLM.

### 20.4 Agregar campo al estado

1. Agregar campo en `src/graph/state.py`.
2. Inicializarlo en estado base (`get_initial_state` o constructor de entrada).
3. Documentar donde se escribe y donde se lee en el flujo.
4. Agregar test de regresion para rutas afectadas.
