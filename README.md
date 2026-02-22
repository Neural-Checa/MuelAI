# MuelAI

Sistema conversacional con LangGraph para consultas odontológicas. Asistente dental inteligente que clasifica consultas, agenda citas y gestiona urgencias.

## Características

- **Clasificación automática** de mensajes en:
  - Consulta General: respuesta automática consultando historial
  - Urgencia Dental: human-in-the-loop para asignar doctores
  - Emergencia Médica: derivación a servicios de emergencia

- **Verificación de pacientes** existentes en el sistema
- **Historial clínico** consultable por el agente
- **Human-in-the-loop** para urgencias dentales

## Requisitos

- Python 3.11+
- Poetry
- API Key de Google Gemini

## Instalación

```bash
# Clonar el repositorio
cd dental-assistant

# Instalar dependencias con Poetry
poetry install

# Configurar variables de entorno
cp .env.example .env
# Editar .env con tu GOOGLE_API_KEY
```

## Ejecución

```bash
# Activar entorno virtual
poetry shell

# Ejecutar la aplicación Streamlit
streamlit run src/main.py
```

## Estructura del Proyecto

```
dental-assistant/
├── src/
│   ├── main.py                 # Entry point Streamlit
│   ├── settings.py             # Configuración
│   ├── database/               # Modelos y conexión SQLite
│   ├── graph/                  # LangGraph (state, nodes, edges)
│   ├── agents/                 # Agentes y prompts
│   ├── services/               # Lógica de negocio
│   └── schemas/                # Pydantic schemas
└── tests/
```

## Flujo del Sistema

1. El paciente escribe su consulta
2. El sistema verifica si es un paciente registrado
3. El clasificador determina el tipo de consulta
4. Se ejecuta el flujo correspondiente según la clasificación
