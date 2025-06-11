from passlib.context import CryptContext
from fastapi.security import OAuth2PasswordBearer

# CryptContext is used for password hashing.
# 'bcrypt' is a strong hashing algorithm recommended for passwords.
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verifies a plain password against a hashed password.
    """
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    """
    Hashes a plain password.
    """
    return pwd_context.hash(password)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/token")
