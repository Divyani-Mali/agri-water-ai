import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import models  # noqa: F401  (registers tables)
from app.core.config import settings
from app.db.database import Base, engine, ensure_schema
from app.routers import admin, alerts, auth, farms, forecast, readings
from app.services.alert_service import run_offline_check

Base.metadata.create_all(bind=engine)
ensure_schema()


async def offline_monitor():
    """Background job: every minute, look for sensors that went silent."""
    while True:
        await asyncio.sleep(60)
        try:
            await asyncio.to_thread(run_offline_check)
        except Exception as exc:  # keep the job alive no matter what
            print(f"[offline monitor] error: {exc}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    task = asyncio.create_task(offline_monitor())
    yield
    task.cancel()


app = FastAPI(title=settings.APP_NAME, version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173", "http://127.0.0.1:5173",
        "http://localhost:3000", "http://127.0.0.1:3000",
        "http://localhost:4200", "http://127.0.0.1:4200",
        "http://localhost:8080", "http://127.0.0.1:8080",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(farms.router)
app.include_router(readings.router)
app.include_router(forecast.router)
app.include_router(alerts.router)
app.include_router(admin.router)


@app.get("/")
def root():
    return {"message": f"{settings.APP_NAME} is running"}


@app.get("/health")
def health():
    return {"status": "ok"}