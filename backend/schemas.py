from pydantic import BaseModel, EmailStr
from typing import Optional

# Pydantic schema for User creation request.
# This defines the data expected when a user signs up.
class UserCreate(BaseModel):
    username: str
    password: str
    email: Optional[EmailStr] = None # Email is optional and validated as an email format

# Pydantic schema for User login request.
# This defines the data expected when a user logs in.
class UserLogin(BaseModel):
    username: str
    password: str

# Pydantic schema for the response after successful login (containing the token).
class Token(BaseModel):
    access_token: str
    token_type: str = "bearer" # Standard token type
