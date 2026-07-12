"""
user.py — Beanie User Model
---------------------------
Defines the MongoDB collection structure for users.

CONCEPT: Beanie ODM (Object Document Mapper) maps Python classes to MongoDB collections.
Unlike SQL databases, you don't need migrations. You just define the schema here,
and Beanie automatically creates the collection and indexes for you.
"""

from datetime import datetime
from typing import Optional
from beanie import Document, Indexed
from pydantic import EmailStr, Field


class User(Document):
    """
    MongoDB document representing a user account.
    """
    email: Indexed(EmailStr, unique=True) = Field(..., description="Unique email address") # type: ignore
    hashed_password: str = Field(..., description="Bcrypt hashed password (NEVER plain text)")
    full_name: str = Field(..., description="User's full name")
    role: str = Field(default="viewer", description="RBAC role: viewer, manager, admin")
    is_active: bool = Field(default=True, description="Account status")
    created_at: datetime = Field(default_factory=datetime.utcnow)

    class Settings:
        name = "users" # MongoDB collection name
        
    def __repr__(self) -> str:
        return f"<User {self.email}>"
