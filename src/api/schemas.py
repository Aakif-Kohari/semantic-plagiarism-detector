"""Pydantic schemas for OpenAPI / Swagger UI response model annotations."""

from __future__ import annotations

from typing import List, Optional, Any, Dict, TypeVar, Generic
from datetime import datetime

from pydantic import BaseModel, Field, ConfigDict


# ============================================================================
# Generic Type Variable for Pagination
# ============================================================================

T = TypeVar('T')


# ============================================================================
# Authentication Schemas
# ============================================================================

class LoginResponse(BaseModel):
    """Response schema for authentication login."""

    token: str = Field(..., description="Authentication session token")


class RefreshRequest(BaseModel):
    """Request schema for token refresh."""

    refresh_token: str | None = Field(
        default=None, description="Valid OAuth2/JWT refresh token"
    )


class TokenResponse(BaseModel):
    """Response schema for OAuth2 Bearer token generation/refresh."""

    access_token: str = Field(
        ..., description="Newly issued OAuth2 Bearer access token"
    )
    token_type: str = Field(default="bearer", description="Token type (bearer)")
    expires_in: int = Field(
        default=3600, description="Token expiration lifetime in seconds"
    )


class RevokeRequest(BaseModel):
    """Request schema for token revocation."""

    token: str | None = Field(default=None, description="API Bearer token to revoke")


class RevokeResponse(BaseModel):
    """Response schema for token revocation."""

    status: str = Field(..., description="Revocation status indicator")
    message: str = Field(
        ..., description="Summary message describing revocation result"
    )


# ============================================================================
# Health Check Schemas
# ============================================================================

class HealthCheckResponse(BaseModel):
    """Response schema for application readiness and liveness probes."""

    status: str = Field(..., description="Health status indicator")
    service: str = Field(..., description="Name of the service")
    version: str = Field(..., description="Service version string")


class HealthzResponse(BaseModel):
    """Response schema for health endpoint."""

    status: str = Field(..., description="Overall service status")
    db: str = Field(..., description="Database connectivity status")
    memory: str = Field(..., description="Memory status")
    db_size_bytes: int = Field(
        default=0, description="Corpus database file size in bytes"
    )
    db_size_mb: float = Field(
        default=0.0, description="Corpus database file size in megabytes"
    )


class StatusResponse(BaseModel):
    """Response schema for the public service status endpoint."""

    status: str = Field(..., description="Service status indicator")
    version: str = Field(..., description="API version string")
    timestamp: str = Field(..., description="Server UTC timestamp in ISO 8601 format")


# ============================================================================
# Pagination Schemas
# ============================================================================

class PaginationParams(BaseModel):
    """
    Request schema for pagination query parameters.
    
    Used to parse pagination parameters from API request query strings.
    """
    page: int = Field(
        default=1, 
        ge=1, 
        description="Page number (1-indexed)"
    )
    per_page: int = Field(
        default=20, 
        ge=1, 
        le=100, 
        description="Number of items per page (max 100)"
    )
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "page": 1,
                "per_page": 20
            }
        }
    )
    
    def get_offset(self) -> int:
        """Calculate offset for database queries."""
        return (self.page - 1) * self.per_page
    
    def get_limit(self) -> int:
        """Get limit for database queries."""
        return self.per_page


class PaginationMeta(BaseModel):
    """
    Pagination metadata model without items.
    
    Useful for responses that need to return pagination info separately
    or for embedding in larger response structures.
    """
    page: int = Field(..., ge=1, description="Current page number (1-indexed)")
    per_page: int = Field(..., ge=1, description="Number of items per page")
    total_items: int = Field(..., ge=0, description="Total number of items across all pages")
    total_pages: int = Field(..., ge=0, description="Total number of pages")
    has_next: bool = Field(False, description="Whether there is a next page")
    has_previous: bool = Field(False, description="Whether there is a previous page")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "page": 1,
                "per_page": 20,
                "total_items": 100,
                "total_pages": 5,
                "has_next": True,
                "has_previous": False
            }
        }
    )


class PaginatedResponse(BaseModel, Generic[T]):
    """
    Generic paginated response model for API endpoints.
    
    This is the main model for paginated responses, providing a consistent
    structure across all API endpoints that return paginated data.
    Mirrors the PaginationPage class structure for standardized OpenAPI generation.
    
    Type Parameters:
        T: The type of items in the response
    
    Attributes:
        items: List of items on the current page
        page: Current page number (1-indexed)
        per_page: Number of items per page
        total_items: Total number of items across all pages
        total_pages: Total number of pages
        has_next: Whether there is a next page
        has_previous: Whether there is a previous page
    """
    items: List[T] = Field(..., description="List of items on the current page")
    page: int = Field(..., ge=1, description="Current page number (1-indexed)")
    per_page: int = Field(..., ge=1, description="Number of items per page")
    total_items: int = Field(..., ge=0, description="Total number of items across all pages")
    total_pages: int = Field(..., ge=0, description="Total number of pages")
    has_next: bool = Field(False, description="Whether there is a next page")
    has_previous: bool = Field(False, description="Whether there is a previous page")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "items": [{"id": 1, "name": "Example Item"}],
                "page": 1,
                "per_page": 20,
                "total_items": 100,
                "total_pages": 5,
                "has_next": True,
                "has_previous": False
            }
        }
    )
    
    @classmethod
    def from_pagination_data(
        cls,
        items: List[T],
        page: int,
        per_page: int,
        total_items: int
    ) -> PaginatedResponse[T]:
        """
        Create a PaginatedResponse from pagination data.
        
        This is a convenience method for constructing responses from raw data.
        
        Args:
            items: List of items on the current page
            page: Current page number (1-indexed)
            per_page: Number of items per page
            total_items: Total number of items across all pages
            
        Returns:
            PaginatedResponse instance
        """
        total_pages = (total_items + per_page - 1) // per_page if total_items > 0 else 0
        
        return cls(
            items=items,
            page=page,
            per_page=per_page,
            total_items=total_items,
            total_pages=total_pages,
            has_next=page < total_pages,
            has_previous=page > 1
        )
    
    def to_pagination_meta(self) -> PaginationMeta:
        """Convert to PaginationMeta model."""
        return PaginationMeta(
            page=self.page,
            per_page=self.per_page,
            total_items=self.total_items,
            total_pages=self.total_pages,
            has_next=self.has_next,
            has_previous=self.has_previous
        )


class CursorPaginationParams(BaseModel):
    """
    Request schema for cursor-based pagination query parameters.
    
    Useful for infinite scrolling and real-time feeds.
    """
    cursor: Optional[str] = Field(
        default=None, 
        description="Cursor for pagination (opaque string)"
    )
    page_size: int = Field(
        default=20, 
        ge=1, 
        le=100, 
        description="Number of items per page (max 100)"
    )
    direction: str = Field(
        default="next",
        description="Pagination direction: 'next' or 'prev'"
    )
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "cursor": "cursor_xyz_123",
                "page_size": 20,
                "direction": "next"
            }
        }
    )


class CursorPaginatedResponse(BaseModel, Generic[T]):
    """
    Cursor-based pagination response model.
    
    Useful for infinite scrolling and real-time feeds where offset-based
    pagination is not ideal.
    """
    items: List[T] = Field(..., description="List of items on the current page")
    next_cursor: Optional[str] = Field(
        default=None, 
        description="Cursor for the next page (null if no more items)"
    )
    prev_cursor: Optional[str] = Field(
        default=None, 
        description="Cursor for the previous page (null if at start)"
    )
    has_more: bool = Field(False, description="Whether there are more items")
    page_size: int = Field(..., ge=1, description="Number of items per page")
    total_items: Optional[int] = Field(
        default=None, 
        ge=0, 
        description="Total items (if known, optional)"
    )
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "items": [{"id": "abc_123", "name": "Item 1"}],
                "next_cursor": "cursor_xyz_456",
                "prev_cursor": "cursor_abc_789",
                "has_more": True,
                "page_size": 20,
                "total_items": 100
            }
        }
    )


# ============================================================================
# Plagiarism Detection Schemas
# ============================================================================

class FlaggedChunkMatch(BaseModel):
    """Schema for individual paragraph or text chunk match pairs."""

    uploaded_chunk: str = Field(
        ..., description="Original text chunk from uploaded document"
    )
    matched_chunk: str = Field(
        ..., description="Matched text chunk from target document"
    )
    similarity_score: float = Field(
        ..., description="Cosine similarity score for chunk pair"
    )


class MatchedDocument(BaseModel):
    """Schema for document matching results in plagiarism detection."""

    filename: str = Field(
        ..., description="Filename of matched target document in corpus"
    )
    document_similarity_score: float = Field(
        ..., description="Overall document similarity score"
    )
    max_chunk_similarity_score: float = Field(
        ..., description="Maximum chunk similarity score"
    )
    severity: str = Field(..., description="Flagged severity level (High, Medium)")
    flagged_chunks: List[FlaggedChunkMatch] = Field(
        default_factory=list, description="List of top matching text chunk pairs"
    )


class SimilarityCheckResponse(BaseModel):
    """Response schema for document plagiarism scanning."""

    filename: str = Field(..., description="Filename of uploaded document")
    word_count: int = Field(..., description="Total word count of uploaded document")
    chunk_count: int = Field(..., description="Total text chunk count")
    plagiarism_flagged: bool = Field(
        ..., description="Whether plagiarism was flagged based on threshold"
    )
    threshold_used: float = Field(
        ..., description="Similarity threshold configured for scan"
    )
    plagiarism_density: int = Field(
        ..., description="Percentage of document chunks flagged as plagiarized"
    )
    overall_document_similarity: float = Field(
        ..., description="Highest overall document similarity score"
    )
    max_chunk_similarity: float = Field(
        ..., description="Highest chunk-level similarity score"
    )
    matched_documents_count: int = Field(
        ..., description="Total count of matched corpus documents"
    )
    matched_documents: List[MatchedDocument] = Field(
        default_factory=list, description="Detailed list of matched corpus documents"
    )


class DocumentUploadResponse(SimilarityCheckResponse):
    """Response schema for document upload and scan operations."""

    pass


class ClearDataResponse(BaseModel):
    """Response schema for bulk clearing administrative operation."""

    status: str = Field(..., description="Operation status (e.g. success)")
    message: str = Field(..., description="Summary message describing clearing action")


class IncidentResponse(ClearDataResponse):
    """Response schema for incident clearing operations."""

    pass


class ErrorResponse(BaseModel):
    """Response schema for API error responses."""

    detail: str = Field(..., description="Detailed error description message")


# ============================================================================
# Asynchronous Job Schemas
# ============================================================================

class AsyncScanJobResponse(BaseModel):
    """Response schema for queuing an asynchronous document scan job."""

    job_id: str = Field(..., description="Unique background scan job identifier")
    status: str = Field(..., description="Initial job status (queued)")
    status_url: str = Field(
        ..., description="Relative endpoint URL to poll for job status"
    )
    message: str = Field(..., description="Status description message")


class AsyncScanStatusResponse(BaseModel):
    """Response schema for checking the status of an asynchronous scan job."""

    job_id: str = Field(..., description="Unique background scan job identifier")
    status: str = Field(
        ..., description="Current job status: queued, processing, completed, or failed"
    )
    filename: str = Field(
        ..., description="Filename of uploaded document being scanned"
    )
    created_at: str = Field(
        ..., description="ISO 8601 UTC timestamp when job was created"
    )
    completed_at: str | None = Field(
        default=None, description="ISO 8601 UTC timestamp when job finished"
    )
    result: SimilarityCheckResponse | None = Field(
        default=None, description="Detailed scan results when completed"
    )
    error: str | None = Field(
        default=None, description="Error message if scan job failed"
    )


# ============================================================================
# Example Paginated Response for Documents
# ============================================================================

# Example document schema (can be extended based on actual document model)
class DocumentSchema(BaseModel):
    """Schema for a document resource."""
    
    id: str = Field(..., description="Document identifier")
    filename: str = Field(..., description="Document filename")
    upload_date: str = Field(..., description="Upload timestamp")
    file_size: int = Field(..., description="File size in bytes")
    content_type: str = Field(..., description="MIME type of the document")
    user_id: Optional[str] = Field(None, description="ID of the user who uploaded")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "id": "doc_123456",
                "filename": "report_2024.pdf",
                "upload_date": "2024-01-01T00:00:00Z",
                "file_size": 1048576,
                "content_type": "application/pdf",
                "user_id": "user_789"
            }
        }
    )


# Document paginated response type alias for convenience
DocumentPaginatedResponse = PaginatedResponse[DocumentSchema]


class DocumentsListResponse(PaginatedResponse[DocumentSchema]):
    """
    Paginated response specifically for document lists.
    
    This extends the generic PaginatedResponse with document-specific
    fields or custom behavior if needed.
    """
    pass


# ============================================================================
# Utility Functions
# ============================================================================

def create_paginated_response(
    items: List[T],
    page: int,
    per_page: int,
    total_items: int
) -> PaginatedResponse[T]:
    """
    Create a paginated response from items and pagination data.
    
    This is a convenience function for creating paginated responses.
    
    Args:
        items: List of items on the current page
        page: Current page number (1-indexed)
        per_page: Number of items per page
        total_items: Total number of items across all pages
        
    Returns:
        PaginatedResponse instance
        
    Example:
        >>> items = [{"id": 1, "name": "Doc 1"}]
        >>> response = create_paginated_response(items, 1, 20, 100)
        >>> response.page
        1
        >>> response.total_pages
        5
    """
    return PaginatedResponse.from_pagination_data(
        items=items,
        page=page,
        per_page=per_page,
        total_items=total_items
    )


def paginated_response_to_dict(
    response: PaginatedResponse[T]
) -> Dict[str, Any]:
    """
    Convert a PaginatedResponse to a dictionary format.
    
    Args:
        response: PaginatedResponse instance
        
    Returns:
        Dictionary representation
        
    Example:
        >>> response = create_paginated_response([], 1, 20, 0)
        >>> paginated_response_to_dict(response)
        {
            'items': [],
            'page': 1,
            'per_page': 20,
            'total_items': 0,
            'total_pages': 0,
            'has_next': False,
            'has_previous': False
        }
    """
    return response.model_dump()


def create_error_response(
    detail: str,
    error_code: Optional[str] = None
) -> ErrorResponse:
    """
    Create a standardized error response.
    
    Args:
        detail: Error message detail
        error_code: Optional error code for debugging
        
    Returns:
        ErrorResponse instance
    """
    # If error code is provided, include it in the detail message
    if error_code:
        detail = f"[{error_code}] {detail}"
    
    return ErrorResponse(detail=detail)


# ============================================================================
# Export all schemas for easy importing
# ============================================================================

__all__ = [
    # Authentication
    'LoginResponse',
    'RefreshRequest',
    'TokenResponse',
    'RevokeRequest',
    'RevokeResponse',
    
    # Health
    'HealthCheckResponse',
    'HealthzResponse',
    'StatusResponse',
    
    # Pagination
    'PaginationParams',
    'PaginationMeta',
    'PaginatedResponse',
    'CursorPaginationParams',
    'CursorPaginatedResponse',
    'DocumentSchema',
    'DocumentPaginatedResponse',
    'DocumentsListResponse',
    'create_paginated_response',
    'paginated_response_to_dict',
    
    # Plagiarism
    'FlaggedChunkMatch',
    'MatchedDocument',
    'SimilarityCheckResponse',
    'DocumentUploadResponse',
    
    # Admin
    'ClearDataResponse',
    'IncidentResponse',
    
    # Errors
    'ErrorResponse',
    'create_error_response',
    
    # Async Jobs
    'AsyncScanJobResponse',
    'AsyncScanStatusResponse',
]
