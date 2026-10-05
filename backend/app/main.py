from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.core.config import settings
from app.db import engine
from app.read_api import router as read_api_router
from app.recommendations.api import router as recommendations_router
from app.simulation import router as simulation_router
from app.waste_detection.api import router as waste_detection_router

app = FastAPI(title="Campus Sustainability Digital Twin API", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(simulation_router)
app.include_router(read_api_router)
app.include_router(waste_detection_router)
app.include_router(recommendations_router)


@app.get("/api/v1/health")
def health_check() -> dict[str, str]:
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
    except SQLAlchemyError as error:
        raise HTTPException(
            status_code=503,
            detail={"status": "unavailable", "database": "unavailable"},
        ) from error

    return {"status": "ok", "database": "connected"}
