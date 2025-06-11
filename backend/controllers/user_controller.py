from fastapi import HTTPException, status, Depends
from sqlalchemy.orm import Session
from backend import models, schemas
from backend.services.user_service import (
    create_user_service,
    authenticate_user_service,
)
from backend.utils.auth import (
    create_access_token,
    get_current_user,
)
from datetime import timedelta

async def signup_controller(user: schemas.UserCreate, db: Session):
    db_user = create_user_service(user, db)
    access_token_expires = timedelta(minutes=30)
    access_token = create_access_token(
        data={"sub": db_user.username}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

async def login_controller(form_data, db: Session):
    user = authenticate_user_service(form_data.username, form_data.password, db)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=30)
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

def get_current_user_controller(
    current_user=Depends(get_current_user)
):
    return current_user
