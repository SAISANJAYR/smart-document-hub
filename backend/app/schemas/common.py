"""
common.py — Shared/Common Pydantic Schemas
------------------------------------------
This file contains reusable, general-purpose data validation schemas
used across various endpoints (e.g., standard error responses, pagination query params).

CONCEPT:
  Pydantic models act as "contracts" for our API. By defining schemas,
  FastAPI automatically generates documentation (Swagger) and performs
  runtime type validation, raising a 422 Unprocessable Entity if parameters are invalid.
"""

from typing import Generic, TypeVar, List
from pydantic import BaseModel, Field

# We use generics so we can reuse PaginatedResponse for any type of model (e.g., users, documents)
T = TypeVar("T")

class PaginatedResponse(BaseModel, Generic[T]):
    """
    Standard pagination response wrapper.
    Ensures consistent paging response schema across all list endpoints.
    """
    items: List[T] = Field(description="List of items for the current page")
    total: int = Field(..., description="Total number of items matching the query")
    page: int = Field(..., description="Current page number (1-indexed)")
    size: int = Field(..., description="Number of items per page")
    pages: int = Field(..., description="Total number of pages available")


class ErrorDetail(BaseModel):
    """
    Detailed error format.
    """
    field: str | None = Field(None, description="The field that caused the error, if applicable")
    message: str = Field(..., description="Human-readable description of the error")


class ErrorResponse(BaseModel):
    """
    Standard error response format for all 4xx and 5xx responses.
    """
    success: bool = Field(False, description="Indicates failure (always false for errors)")
    error: str = Field(..., description="Brief error code/type (e.g., 'not_found', 'validation_error')")
    detail: str | List[ErrorDetail] = Field(..., description="Detailed message or list of field-specific errors")
