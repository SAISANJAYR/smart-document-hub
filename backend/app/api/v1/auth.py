"""
auth.py — Authentication Router
--------------------------------
Contains endpoints for user registration, login, and token refreshing.
These are stubs for Day 2 to demonstrate Pydantic schema validation.
"""

from datetime import datetime
from fastapi import APIRouter, HTTPException, status
from app.schemas.user import UserCreate, UserLogin, UserResponse, Token

router = APIRouter()


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(user_in: UserCreate):
    """
    Register a new user account.
    FastAPI will automatically validate that:
    - Email is formatted correctly.
    - Password is at least 8 characters.
    - Full name is provided.
    """
    # Stub response representing successful DB insertion (implemented in Week 2)
    return UserResponse(
        id="user_mock_123456",
        email=user_in.email,
        full_name=user_in.full_name,
        role="viewer",
        is_active=True,
        created_at=datetime.utcnow()
    )


@router.post("/login", response_model=Token)
async def login(credentials: UserLogin):
    """
    Authenticate user and return access/refresh tokens.
    """
    # Simple mock check for demonstration
    if credentials.email == "fail@example.com":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password"
        )
        
    mock_user = UserResponse(
        id="user_mock_123456",
        email=credentials.email,
        full_name="Mock User",
        role="viewer",
        is_active=True,
        created_at=datetime.utcnow()
    )
    
    return Token(
        access_token="mock_jwt_access_token_xyz123",
        refresh_token="mock_jwt_refresh_token_abc789",
        token_type="bearer",
        user=mock_user
    )
