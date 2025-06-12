# uvicorn main:app --reload --port 8000
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


from fastapi import FastAPI
from backend.database import engine, Base, init_db
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# --- Database Initialization ---
# Ensure all tables are created before the app starts, even if only 'users' exists.
from sqlalchemy.exc import OperationalError

def safe_init_db():
    try:
        print("[DB INIT] Attempting to create all tables if they do not exist...")
        init_db()  # This will create all tables if they do not exist

        # --- DEBUG: Force table creation if missing ---
        from sqlalchemy import inspect
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        print(f"[DB INIT] Tables present after init: {tables}")

        # If 'chats' or 'messages' missing, force create again and re-check
        missing = []
        for t in ["chats", "messages"]:
            if t not in tables:
                missing.append(t)
        if missing:
            print(f"[DB INIT] Forcing creation of missing tables: {missing}")
            Base.metadata.create_all(bind=engine)
            tables = inspect(engine).get_table_names()
            print(f"[DB INIT] Tables present after forced create: {tables}")
            if all(t in tables for t in ["chats", "messages"]):
                print("[DB INIT] 'chats' and 'messages' tables now exist.")
            else:
                print("[DB INIT] ERROR: Some tables are still missing after forced create.")
        else:
            print("[DB INIT] 'chats' and 'messages' tables exist or were created successfully.")
    except OperationalError as e:
        print(f"[DB INIT] Database error: {e}")
        raise
    except Exception as e:
        print(f"[DB INIT] Unexpected error during DB init: {e}")
        raise

safe_init_db()

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

