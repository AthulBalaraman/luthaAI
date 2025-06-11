# uvicorn main:app --reload --port 8000
import sys
import os
# Add the project root to sys.path so 'backend' can be imported when running this file directly
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
  
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from backend import models, schemas, auth # Import your database models, schemas, and auth functions
from backend.database import engine, get_db, Base
from dotenv import load_dotenv
from datetime import datetime, timedelta
import jwt # Python JWT library (pyjwt)
from typing import Optional
from fastapi.security import OAuth2PasswordRequestForm
from fastapi import Header
from jose import JWTError
from fastapi import File, UploadFile
import shutil
import tempfile
from pathlib import Path
from typing import List

# Load environment variables
load_dotenv()

# --- Database Initialization ---
# Create all tables defined in models.py in the database.
# This should typically be done once when the application starts or during deployment setup.
# For simplicity in development, we call it directly here. In production, use Alembic for migrations.
Base.metadata.create_all(bind=engine)

# --- FastAPI Application Setup ---
app = FastAPI(
    title="LuthaMind AI Backend API",
    description="API for user authentication and LLM interaction for LuthaMind AI.",
    version="1.0.0"
)

# --- JWT Configuration (Placeholder for now) ---
# In a real application, these would be managed more robustly and securely.
SECRET_KEY = os.getenv("SECRET_KEY", "super_secret_fallback_key_do_not_use_in_prod")
ALGORITHM = os.getenv("ALGORITHM", "HS256")

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """
    Creates a JWT access token.
    For this sprint, this is a simplified version. 
    """
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=30) # Default expiry
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def get_current_user(token: str = Depends(auth.oauth2_scheme), db: Session = Depends(get_db)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    user = db.query(models.User).filter(models.User.username == username).first()
    if user is None:
        raise credentials_exception
    return user

# --- File Upload Configuration ---
ALLOWED_MIME_TYPES = {
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document", # .docx
    "text/plain"
}

def validate_file(upload_file: UploadFile):
    """
    Validates the uploaded file's MIME type.
    Raises HTTPException if unsupported.
    """
    if upload_file.content_type not in ALLOWED_MIME_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file type: {upload_file.content_type}"
        )

def save_upload_file(upload_file: UploadFile) -> Path:
    """
    Saves the uploaded file to a temporary file on disk.
    Returns the path to the saved file.
    """
    try:
        suffix = Path(upload_file.filename).suffix
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            shutil.copyfileobj(upload_file.file, tmp)
            temp_path = Path(tmp.name)
        print(f"[UPLOAD] Saved file '{upload_file.filename}' to temp path: {temp_path}")  # <-- Add this line for visibility
        return temp_path
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to save uploaded file: {str(e)}"
        )

def parse_document_content(path: Path, mime_type: str) -> str:
    """
    Parses the given document file and returns its raw text content.

    Supported file types:
    - PDF: Uses pdfplumber for robust text extraction (handles complex layouts, tables, etc.).
    - DOCX: Uses python-docx to extract paragraphs.
    - TXT/Markdown: Reads as UTF-8 text.

    Future hooks:
    - Add chunking, embedding, and metadata extraction here.

    Raises:
        HTTPException: If extraction fails or no text is found.
    """
    try:
        if mime_type == "application/pdf":
            import pdfplumber
            try:
                with pdfplumber.open(str(path)) as pdf:
                    texts = []
                    for page in pdf.pages:
                        page_text = page.extract_text()
                        if page_text:
                            texts.append(page_text)
                raw_text = "\n".join(texts)
            except Exception as e:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"PDF parsing failed: {str(e)}"
                )
        elif mime_type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
            try:
                from docx import Document
                doc = Document(str(path))
                raw_text = "\n".join([para.text for para in doc.paragraphs if para.text.strip()])
            except Exception as e:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"DOCX parsing failed: {str(e)}"
                )
        elif mime_type in ("text/plain", "text/markdown"):
            try:
                raw_text = path.read_text(encoding="utf-8")
            except Exception as e:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Text file reading failed: {str(e)}"
                )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported MIME type for parsing: {mime_type}"
            )

        if not raw_text or not raw_text.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No text extracted"
            )
        return raw_text

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Document parsing error: {str(e)}"
        )

# --- API Endpoints ---

@app.get("/")
async def read_root():
    """Root endpoint for the API."""
    return {"message": "Welcome to LuthaMind AI Backend API!"}

@app.post("/signup", response_model=schemas.Token, status_code=status.HTTP_201_CREATED)
async def signup(user: schemas.UserCreate, db: Session = Depends(get_db)):
    """
    Registers a new user.
    Hashes the password and stores the user in the database.
    """ 
    # Check if username or email already exists
    db_user_username = db.query(models.User).filter(models.User.username == user.username).first()
    if db_user_username:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Username already registered")
    
    if user.email: # Check email only if provided
        db_user_email = db.query(models.User).filter(models.User.email == user.email).first()
        if db_user_email:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered")

    # Hash the password before storing it
    hashed_password = auth.get_password_hash(user.password)
    
    # Create a new User instance
    db_user = models.User(username=user.username, hashed_password=hashed_password, email=user.email)
    
    # Add to session and commit to database
    db.add(db_user)
    db.commit()
    db.refresh(db_user) # Refresh to get the auto-generated ID and created_at

    # Create a simple access token for the newly registered user
    access_token_expires = timedelta(minutes=30)
    access_token = create_access_token(
        data={"sub": db_user.username}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

@app.post("/token", response_model=schemas.Token)
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    """
    Authenticates a user and returns an access token if credentials are valid.
    """
    user = db.query(models.User).filter(models.User.username == form_data.username).first()
    if not user or not auth.verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Create a simple access token for the authenticated user
    access_token_expires = timedelta(minutes=30)
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

@app.get("/current_user")
async def read_current_user(current_user: models.User = Depends(get_current_user)):
    """
    Returns the current user's username and email.
    """
    return {"username": current_user.username, "email": current_user.email}

@app.post("/upload_document")
async def upload_document(
    files: List[UploadFile] = File(...),
    current_user: models.User = Depends(get_current_user)
):
    """
    Receives authenticated file uploads, validates, saves temporarily, parses content, and returns metadata.
    """
    if not files or len(files) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No files uploaded."
        )

    metadata_list = []
    temp_files = []
    parsed_docs = []  # Store parsed text and metadata for future chunking

    for upload_file in files:
        validate_file(upload_file)
        try:
            temp_path = save_upload_file(upload_file)
            temp_files.append(temp_path)
            size = temp_path.stat().st_size

            # --- Parse document content ---
            try:
                raw_text = parse_document_content(temp_path, upload_file.content_type)
                parsed_docs.append({
                    "filename": upload_file.filename,
                    "content_type": upload_file.content_type,
                    "size": size,
                    "raw_text": raw_text,
                })
            except HTTPException as e:
                for f in temp_files:
                    try:
                        f.unlink(missing_ok=True)
                    except Exception:
                        pass
                raise

            metadata_list.append({
                "filename": upload_file.filename,
                "content_type": upload_file.content_type,
                "size": size,
                "text_preview": raw_text[:200]  # Show a preview for debugging
            })
            # --- Future: Add document chunking, embedding, and cleanup here ---

        except Exception as e:
            for f in temp_files:
                try:
                    f.unlink(missing_ok=True)
                except Exception:
                    pass
            raise

    # Note: temp files are not deleted here; add cleanup after downstream processing in future
    return {"files": metadata_list}

