"""
auth.py — Authentication Router
--------------------------------
Contains endpoints for user registration, login, and token refreshing.
Now wired up to MongoDB and JWT utilities!
"""

from datetime import datetime
from fastapi import APIRouter, HTTPException, status
from app.schemas.user import UserCreate, UserLogin, UserResponse, Token
from app.models.user import User
from app.core.auth.hashing import get_password_hash, verify_password
from app.core.auth.jwt import create_access_token, create_refresh_token, ALGORITHM

router = APIRouter()


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(user_in: UserCreate):
    """
    Register a new user account.
    """
    # 1. Check if user already exists
    existing_user = await User.find_one(User.email == user_in.email)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A user with this email already exists."
        )
        
    # 2. Hash the password
    hashed_password = get_password_hash(user_in.password)
    
    # 3. Create the Database Model
    new_user = User(
        email=user_in.email,
        hashed_password=hashed_password,
        full_name=user_in.full_name,
        role="viewer",
        is_active=True
    )
    
    # 4. Save to MongoDB
    await new_user.insert()
    
    # Beanie assigns a MongoDB ObjectId to `new_user.id` upon insertion.
    # The response_model=UserResponse will automatically parse it and hide the hashed_password!
    return new_user


@router.post("/login", response_model=Token)
async def login(credentials: UserLogin):
    """
    Authenticate user and return access/refresh tokens.
    """
    # 1. Fetch user from MongoDB
    user = await User.find_one(User.email == credentials.email)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password" # We don't say "User not found" to prevent email enumeration hacking
        )
        
    # 2. Verify password
    if not verify_password(credentials.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password"
        )
        
    # 3. Generate JWT tokens
    # We embed the user's ID string (sub = subject) and role in the token payload
    token_payload = {"sub": str(user.id), "role": user.role}
    
    access_token = create_access_token(data=token_payload)
    refresh_token = create_refresh_token(data=token_payload)
    
    return Token(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        user=user # The Pydantic schema will strip the password from this object automatically
    )


from app.schemas.user import TokenRefreshRequest
from jose import jwt, JWTError
from app.config import settings
from bson import ObjectId

@router.post("/refresh", response_model=Token)
async def refresh_token(request: TokenRefreshRequest):
    """
    Get a new access token using a valid refresh token.
    This prevents users from being logged out when their short-lived access token expires.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
    )
    
    try:
        # Decode the refresh token
        payload = jwt.decode(request.refresh_token, settings.SECRET_KEY, algorithms=[ALGORITHM])
        
        # Ensure this is actually a refresh token
        if payload.get("type") != "refresh":
            raise credentials_exception
            
        user_id: str | None = payload.get("sub")
        if user_id is None:
            raise credentials_exception
            
    except JWTError:
        raise credentials_exception
        
    # Fetch user to make sure they still exist and are active
    user = await User.get(ObjectId(user_id))
    if not user or not user.is_active:
        raise credentials_exception
        
    # Generate fresh tokens
    token_payload = {"sub": str(user.id), "role": user.role}
    new_access_token = create_access_token(data=token_payload)
    new_refresh_token = create_refresh_token(data=token_payload)
    
    return Token(
        access_token=new_access_token,
        refresh_token=new_refresh_token,
        token_type="bearer",
        user=user
    )


# Role-Based Access Control (RBAC) demonstration
from app.core.auth.dependencies import RoleChecker
from fastapi import Depends

@router.get("/admin/stats", dependencies=[Depends(RoleChecker(["admin"]))])
async def get_admin_stats():
    """
    An endpoint only accessible to users with the 'admin' role.
    If a 'viewer' or 'manager' tries to access this, they get a 403 Forbidden.
    """
    total_users = await User.count()
    return {
        "message": "Welcome to the admin dashboard",
        "total_users": total_users,
        "system_status": "Healthy"
    }
