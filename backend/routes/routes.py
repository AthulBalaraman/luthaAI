from fastapi import APIRouter, Depends, status, UploadFile, File
from typing import List
from sqlalchemy.orm import Session
from fastapi.security import OAuth2PasswordRequestForm

from backend.schemas import UserCreate, Token
from backend.database import get_db
from backend.controllers.user_controller import (
    signup_controller,
    login_controller,
    get_current_user_controller,
)
from backend.controllers.document_controller import upload_document_controller
from backend.models import User

router = APIRouter()

@router.post("/signup", response_model=Token, status_code=status.HTTP_201_CREATED)
async def signup(user: UserCreate, db: Session = Depends(get_db)):
    return await signup_controller(user, db)

@router.post("/token", response_model=Token)
async def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    return await login_controller(form_data, db)

@router.get("/current_user")
async def read_current_user(current_user: User = Depends(get_current_user_controller)):
    # Ensure current_user is a valid User instance
    return {"username": current_user.username, "email": current_user.email}

@router.post("/upload_document")
async def upload_document(
    files: List[UploadFile] = File(...),
    current_user: User = Depends(get_current_user_controller)
):
    return await upload_document_controller(files, current_user)
