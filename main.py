from contextlib import asynccontextmanager

from fastapi import FastAPI

from src.api.webhook import router as webhook_router
from src.database.connection import init_db, seed_demo_data


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    seed_demo_data()
    yield


app = FastAPI(title="MuelAI API", lifespan=lifespan)
app.include_router(webhook_router, prefix="/webhook")


@app.get("/")
def health_check() -> dict[str, str]:
    return {"status": "ok", "service": "MuelAI"}
