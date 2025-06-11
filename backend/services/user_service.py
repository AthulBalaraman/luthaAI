from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from backend import models, schemas
from backend.utils.auth import get_password_hash, verify_password

def create_user_service(user: schemas.UserCreate, db: Session):
    db_user_username = db.query(models.User).filter(models.User.username == user.username).first()
    if db_user_username:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Username already registered")
    if user.email:
        db_user_email = db.query(models.User).filter(models.User.email == user.email).first()
        if db_user_email:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered")
    hashed_password = get_password_hash(user.password)
    db_user = models.User(username=user.username, hashed_password=hashed_password, email=user.email)
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

def authenticate_user_service(username: str, password: str, db: Session):
    user = db.query(models.User).filter(models.User.username == username).first()
    if not user or not verify_password(password, user.hashed_password):
        return None
    return user
