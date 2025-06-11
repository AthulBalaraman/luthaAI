# uvicorn main:app --reload --port 8000
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


from fastapi import FastAPI
from backend.database import engine, Base
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# --- Database Initialization ---
Base.metadata.create_all(bind=engine)

# --- FastAPI Application Setup ---
app = FastAPI(
    title="LuthaMind AI Backend API",
    description="API for user authentication and LLM interaction for LuthaMind AI.",
    version="1.0.0"
)

# --- Include Routers ---
from backend.routes.routes import router as api_router
app.include_router(api_router)

# Optionally, you can keep a root endpoint here
@app.get("/")
async def read_root():
    """Root endpoint for the API."""
    return {"message": "Welcome to LuthaMind AI Backend API!"}

