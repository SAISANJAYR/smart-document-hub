"""
dependencies.py — FastAPI Dependency Injection for Auth
-------------------------------------------------------
This is where FastAPI's magic happens. We define a dependency `get_current_user`.
Any route that includes `user = Depends(get_current_user)` will automatically:
1. Extract the JWT from the Authorization header.
2. Validate the signature and expiration.
3. Fetch the user from MongoDB.
4. Block the request if anything is wrong.
"""

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import jwt, JWTError
from bson import ObjectId
from typing import List

from app.config import settings
from app.models.user import User
from app.core.auth.jwt import ALGORITHM

# This tells FastAPI where the client can get a token (used by Swagger UI)
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")

async def get_current_user(token: str = Depends(oauth2_scheme)) -> User:
    """
    Validates the token and returns the current MongoDB User object.
    Raises 401 Unauthorized if the token is invalid, expired, or the user is deleted.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        # 1. Decode the token using our secret key
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGORITHM])
        
        # 2. Extract the user ID (subject)
        user_id: str | None = payload.get("sub")
        if user_id is None:
            raise credentials_exception
            
    except JWTError:
        # If the token is expired or tampered with, jwt.decode throws an error
        raise credentials_exception
        
    # 3. Fetch the user from the database
    user = await User.get(ObjectId(user_id))
    if user is None:
        raise credentials_exception
        
    # 4. Check if the account was deactivated
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail="Inactive user account"
        )
        
    return user


class RoleChecker:
    """
    A dependency class to enforce Role-Based Access Control (RBAC).
    Usage:
        Depends(RoleChecker(["admin", "manager"]))
    """
    def __init__(self, allowed_roles: List[str]):
        self.allowed_roles = allowed_roles

    def __call__(self, current_user: User = Depends(get_current_user)):
        if current_user.role not in self.allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Operation not permitted. Required roles: {', '.join(self.allowed_roles)}"
            )
        return current_user
