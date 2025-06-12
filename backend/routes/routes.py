from fastapi import APIRouter, Depends, status, UploadFile, File, HTTPException
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
from backend import models  # <-- Add this import at the top

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

@router.get("/user_chats")
async def get_user_chats(current_user: User = Depends(get_current_user_controller), db: Session = Depends(get_db)):
    """
    Return all chat threads (chat_ids) for the current user.
    """
    chats = db.query(models.Chat).filter(models.Chat.user_id == current_user.id).all()
    return {"chats": [{"chat_id": c.id, "name": c.name} for c in chats]}

@router.post("/create_chat", status_code=status.HTTP_201_CREATED)
async def create_chat(current_user: User = Depends(get_current_user_controller), db: Session = Depends(get_db)):
    """
    Create a new chat thread for the user.
    """
    from backend.models import Chat
    chat = Chat(user_id=current_user.id, name="New Chat")
    db.add(chat)
    db.commit()
    db.refresh(chat)
    return {"chat_id": chat.id}

@router.get("/chat/{chat_id}/messages")
async def get_chat_messages(
    chat_id: int,
    page: int = 1,
    per_page: int = 20,
    current_user: User = Depends(get_current_user_controller),
    db: Session = Depends(get_db)
):
    """
    Return paginated messages for a chat, only if user owns the chat.
    Always return a valid response, even if there are no messages yet.
    """
    chat = db.query(models.Chat).filter(models.Chat.id == chat_id, models.Chat.user_id == current_user.id).first()
    if not chat:
        raise HTTPException(status_code=403, detail="Not authorized for this chat.")
    total_messages = db.query(models.Message).filter(models.Message.chat_id == chat_id).count()
    total_pages = max(1, (total_messages + per_page - 1) // per_page)
    messages = (
        db.query(models.Message)
        .filter(models.Message.chat_id == chat_id)
        .order_by(models.Message.id.asc())
        .offset((page - 1) * per_page)
        .limit(per_page)
        .all()
    )
    # Always return a valid response, even if messages is empty
    return {
        "messages": [{"role": m.role, "content": m.content} for m in messages],
        "total_pages": total_pages
    }

@router.post("/chat/{chat_id}/send_message", status_code=201)
async def send_message_to_chat(
    chat_id: int,
    data: dict,
    current_user: User = Depends(get_current_user_controller),
    db: Session = Depends(get_db)
):
    """
    Add a message to a chat, only if user owns the chat.
    Accepts both user and assistant messages.
    """
    chat = db.query(models.Chat).filter(models.Chat.id == chat_id, models.Chat.user_id == current_user.id).first()
    if not chat:
        raise HTTPException(status_code=403, detail="Not authorized for this chat.")
    from backend.models import Message
    role = data.get("role", "user")
    msg = Message(chat_id=chat_id, role=role, content=data.get("content", ""))
    db.add(msg)
    db.commit()
    db.refresh(msg)
    return {"message_id": msg.id}
