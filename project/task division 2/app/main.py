from fastapi import FastAPI
from app.database import test_connection

app = FastAPI(title="UniSphere API")

@app.get("/")
def home():
    return {"message": "UniSphere API is running"}

@app.get("/test-db")
def test_db():
    result = test_connection()

    return {
        "status": "Connected successfully",
        "database": result[0],
        "user": result[1]
    }