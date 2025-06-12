from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from .database import Base # Import Base from your database setup

# Define the User model which maps to the 'users' table in your database.
class User(Base):
    __tablename__ = "users" # Name of the table in the database

    # Define columns for the 'users' table.
    id = Column(Integer, primary_key=True, index=True) # Primary key, auto-incrementing
    username = Column(String(50), unique=True, index=True, nullable=False) # Unique username
    hashed_password = Column(String(255), nullable=False) # Stores the hashed password
    email = Column(String(100), unique=True, index=True, nullable=True) # Optional email, unique
    created_at = Column(DateTime, server_default=func.now()) # Timestamp for user creation
    chats = relationship("Chat", back_populates="user")

    # A __repr__ method for better representation when printing User objects (useful for debugging).
    def __repr__(self):
        return f"<User(id={self.id}, username='{self.username}', email='{self.email}')>"

class Chat(Base):
    __tablename__ = "chats"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    name = Column(String(100), default="New Chat")
    created_at = Column(DateTime, server_default=func.now())
    user = relationship("User", back_populates="chats")
    messages = relationship("Message", back_populates="chat")

class Message(Base):
    __tablename__ = "messages"
    id = Column(Integer, primary_key=True, index=True)
    chat_id = Column(Integer, ForeignKey("chats.id"), nullable=False)
    role = Column(String(20), nullable=False)  # "user" or "assistant"
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, server_default=func.now())
    chat = relationship("Chat", back_populates="messages")
