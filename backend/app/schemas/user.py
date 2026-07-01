"""
user.py — User Pydantic Schemas
--------------------------------
This file defines validation schemas for user-related requests and responses.

KEY CONCEPTS:
  1. EmailStr - Validates email format automatically (requires `email-validator` package, which is in requirements.txt).
  2. Field() - Adds metadata like descriptions, constraints (min/max length), and example values.
  3. Response Schemas - Excludes sensitive information like the password hash when returning user data.
"""

from datetime import datetime
from pydantic import BaseModel, EmailStr, Field


class UserBase(BaseModel):
    """
    Shared attributes for User schemas.
    """
    email: EmailStr = Field(..., description="User's unique email address", examples=["user@example.com"])
    full_name: str = Field(..., min_length=2, max_length=100, description="User's full name", examples=["SaiSanjay R"])


class UserCreate(UserBase):
    """
    Schema for user registration requests.
    Validates password strength rules.
    """
    password: str = Field(..., min_length=8, max_length=128, description="User's password (min 8 characters)")


class UserLogin(BaseModel):
    """
    Schema for authentication requests.
    """
    email: EmailStr = Field(..., description="User's email address")
    password: str = Field(..., description="User's password")


class UserResponse(UserBase):
    """
    Schema for returning User details in API responses.
    Notice we DO NOT include the password here.
    """
    id: str = Field(..., description="The unique database ID of the user (represented as string)")
    role: str = Field("viewer", description="User's access control role (viewer, manager, admin)")
    is_active: bool = Field(True, description="Whether the user account is active")
    created_at: datetime = Field(..., description="Timestamp of when the user was created")

    model_config = {
        "from_attributes": True  # Allows loading from Beanie ODM or SQLAlchemy models directly
    }


class Token(BaseModel):
    """
    Schema for JWT tokens returned on successful login.
    """
    access_token: str = Field(..., description="The JWT access token used in the Authorization header")
    refresh_token: str = Field(..., description="The refresh token used to request new access tokens")
    token_type: str = Field("bearer", description="Token scheme type (always 'bearer')")
    user: UserResponse = Field(..., description="The authenticated user's details")


class TokenData(BaseModel):
    """
    Internal schema for decoded JWT payload data.
    """
    sub: str | None = None
    role: str | None = None
