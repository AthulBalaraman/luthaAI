from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Get the database URL from environment variables.
# This makes your database credentials secure and configurable.
DATABASE_URL = os.getenv("DATABASE_URL")

# Create a SQLAlchemy engine. The 'pool_pre_ping=True' helps maintain connection health.
# 'echo=False' prevents SQLAlchemy from printing all SQL queries to the console, set to True for debugging.
engine = create_engine(DATABASE_URL, pool_pre_ping=True, echo=False)

# Create a SessionLocal class. Each instance of SessionLocal will be a database session.
# 'autocommit=False' means changes won't be committed until .commit() is called.
# 'autoflush=False' means objects won't be flushed to the database until explicitly committed or flushed.
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for your database models.
Base = declarative_base()

# Dependency to get a database session.
# This function will be used by FastAPI to provide a database session for each request.
def get_db():
    db = SessionLocal() # Create a new session
    try:
        yield db # Provide the session to the calling function
    finally:
        db.close() # Ensure the session is closed after the request is processed

# Ensure all tables are created (including Chat and Message)
def init_db():
    Base.metadata.create_all(bind=engine)

# At the bottom of the file, for manual creation (optional):
if __name__ == "__main__":
    Base.metadata.create_all(bind=engine)
