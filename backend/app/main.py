from fastapi import FastAPI
from sqlalchemy import text
from fastapi import Depends
from sqlalchemy.orm import Session
from app.database.connection import get_db

from app.database.connection import engine

app = FastAPI(
    title="UniSphere API",
    description="Intelligent Multi-Agent University ERP System",
    version="1.0.0",
)


@app.get("/")
def root():
    return {"message": "Welcome to UniSphere API"}


@app.get("/health/database")
def database_health():
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))

        return {
            "status": "healthy",
            "database": "connected",
            "message": "UniSphere is successfully connected to Neon PostgreSQL."
        }

    except Exception as error:
        return {
            "status": "unhealthy",
            "database": "disconnected",
            "error": str(error)
        }
@app.get("/health/db-session")
def test_db_session(db: Session = Depends(get_db)):
        db.execute(text("SELECT 1"))
        return {
            "status": "healthy",
            "message": "FastAPI database session dependency is working."
        }