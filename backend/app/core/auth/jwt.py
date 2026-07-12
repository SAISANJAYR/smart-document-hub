"""
jwt.py — JSON Web Token Utilities
---------------------------------
Generates and decodes JWTs used to authenticate users on every request.

CONCEPT:
A JWT (JSON Web Token) is like a digital VIP wristband.
When a user logs in with the correct email/password, we give them this token.
For all future requests (like uploading a file), they just show the token.
Since the token is cryptographically signed with our SECRET_KEY, we know it's valid
and hasn't been tampered with.
"""

from datetime import datetime, timedelta
from jose import jwt
from app.config import settings

# In JWT terminology, ALGORITHM defines how the signature is computed.
# HS256 is HMAC with SHA-256 (very standard and secure).
ALGORITHM = "HS256"

def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    """
    Creates a JWT access token encoding the provided data (usually user ID).
    """
    # 1. Make a copy of the data payload so we don't accidentally mutate the original dictionary
    to_encode = data.copy()
    
    # 2. Determine expiration time. If not provided, use default from settings.
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        
    # 3. Add the 'exp' (expiration) claim. This is a standard JWT field.
    to_encode.update({"exp": expire})
    
    # 4. Create and cryptographically sign the JWT using our SECRET_KEY.
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=ALGORITHM)
    
    return encoded_jwt


def create_refresh_token(data: dict) -> str:
    """
    Creates a JWT refresh token, which lives much longer than an access token.
    Used to get a new access token without making the user log in again.
    """
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire, "type": "refresh"})
    
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt
