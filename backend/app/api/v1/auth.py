"""
auth.py — Registration, login, token refresh, current user, and an RBAC-protected admin route.
"""

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, status
from jose import JWTError, jwt

from app.config import settings
from app.core.auth.dependencies import RoleChecker, get_current_user
from app.core.auth.hashing import get_password_hash, verify_password
from app.core.auth.jwt import ALGORITHM, create_access_token, create_refresh_token
from app.core.rate_limit import RateLimit
from app.models.document import DocumentModel
from app.models.user import User
from app.schemas.user import Token, TokenRefreshRequest, UserCreate, UserLogin, UserResponse

router = APIRouter()


def _tokens(user: User) -> Token:
    payload = {"sub": str(user.id), "role": user.role}
    return Token(access_token=create_access_token(payload), refresh_token=create_refresh_token(payload),
                 token_type="bearer", user=user)


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED,
             dependencies=[Depends(RateLimit(times=10, seconds=60))])
async def register(user_in: UserCreate):
    if await User.find_one(User.email == user_in.email):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="A user with this email already exists.")
    user = User(email=user_in.email, hashed_password=get_password_hash(user_in.password),
                full_name=user_in.full_name, role="viewer", is_active=True)
    await user.insert()
    return user


@router.post("/login", response_model=Token, dependencies=[Depends(RateLimit(times=10, seconds=60))])
async def login(credentials: UserLogin):
    user = await User.find_one(User.email == credentials.email)
    # Same message for unknown email and wrong password, to prevent account enumeration.
    if not user or not verify_password(credentials.password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect email or password")
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="This account is disabled")
    return _tokens(user)


@router.post("/refresh", response_model=Token)
async def refresh_token(request: TokenRefreshRequest):
    bad = HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Could not validate credentials")
    try:
        payload = jwt.decode(request.refresh_token, settings.SECRET_KEY, algorithms=[ALGORITHM])
        if payload.get("type") != "refresh" or not payload.get("sub"):
            raise bad
    except JWTError:
        raise bad
    user = await User.get(ObjectId(payload["sub"]))
    if not user or not user.is_active:
        raise bad
    return _tokens(user)


@router.get("/me", response_model=UserResponse)
async def me(current_user: User = Depends(get_current_user)):
    return current_user


@router.get("/admin/stats", dependencies=[Depends(RoleChecker(["admin"]))])
async def get_admin_stats():
    return {
        "total_users": await User.count(),
        "total_documents": await DocumentModel.count(),
        "system_status": "healthy",
    }
