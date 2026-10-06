from pydantic import BaseModel, Field, field_validator
from typing import Dict, List, Optional, Any
from datetime import datetime
from enum import Enum
import json

from backend.models.common import BaseResponse


# ============================================================================
# Shared Validators
# ============================================================================

def validate_iso_ts(value: Optional[str]) -> Optional[str]:
    """Validate ISO-8601 timestamp format."""
    if value is None:
        return value
    if isinstance(value, datetime):
        return value.isoformat()
    try:
        datetime.fromisoformat(value.replace("Z", "+00:00"))
        return value
    except ValueError as exc:
        raise ValueError(f"Invalid ISO-8601 timestamp: {value}") from exc


def validate_max_len(value: Optional[str], max_length: int, field_name: str) -> Optional[str]:
    """Validate maximum string length."""
    if value is None:
        return value
    if len(value) > max_length:
        raise ValueError(f"{field_name} exceeds maximum length of {max_length} characters")
    return value


def validate_json_serializable(value: Any) -> Any:
    """Ensure value is JSON-serializable."""
    if value is None:
        return value
    try:
        json.dumps(value)
        return value
    except (TypeError, ValueError) as exc:
        raise ValueError(f"Value must be JSON-serializable: {exc}") from exc


# ============================================================================
# Main Models
# ============================================================================

class AssetMetadata(BaseModel):
    """Asset metadata model for Dataverse storage"""

    id: str = Field(..., description="Unique asset identifier (GUID)")
    media_type: str = Field(
        ..., description="Media type (image/video)"
    )
    blob_name: str = Field(..., description="Asset name in Dataverse")
    container: str = Field(..., description="Dataverse container reference")
    url: str = Field(..., description="URL to access the asset")
    filename: str = Field(..., description="Original filename")
    size: int = Field(..., description="File size in bytes")
    content_type: Optional[str] = Field(None, description="MIME content type")
    folder_path: Optional[str] = Field("", description="Folder path in storage")

    # AI-generated content metadata
    prompt: Optional[str] = Field(None, description="Generation prompt")
    model: Optional[str] = Field(None, description="AI model used")
    generation_id: Optional[str] = Field(None, description="Generation job ID")

    # Analysis results
    summary: Optional[str] = Field(None, description="AI-generated summary")
    description: Optional[str] = Field(None, description="AI-generated description")
    products: Optional[str] = Field(None, description="Identified products/brands")
    tags: Optional[List[str]] = Field(None, description="Metadata tags")
    feedback: Optional[str] = Field(None, description="AI feedback")

    # Technical metadata
    quality: Optional[str] = Field(None, description="Generation quality setting")
    background: Optional[str] = Field(None, description="Background setting")
    output_format: Optional[str] = Field(None, description="Output format")
    has_transparency: Optional[bool] = Field(
        None, description="Has transparent background"
    )

    # Video-specific metadata
    duration: Optional[float] = Field(None, description="Video duration in seconds")
    fps: Optional[float] = Field(None, description="Frames per second")
    resolution: Optional[str] = Field(None, description="Video resolution")

    # Custom metadata
    custom_metadata: Optional[Dict[str, Any]] = Field(
        None, description="Additional custom metadata (JSON-serializable)"
    )

    # Timestamps and system fields
    created_at: str = Field(..., description="Creation timestamp (ISO-8601)")
    updated_at: str = Field(..., description="Last update timestamp (ISO-8601)")
    doc_type: str = Field(
        default="asset_metadata", description="Document type for querying"
    )

    # Validators
    @field_validator("created_at", "updated_at")
    @classmethod
    def validate_timestamps(cls, v: Optional[str]) -> Optional[str]:
        """Validate ISO-8601 timestamps."""
        return validate_iso_ts(v)

    @field_validator("prompt")
    @classmethod
    def validate_prompt_length(cls, v: Optional[str]) -> Optional[str]:
        """Validate prompt does not exceed 4000 characters."""
        return validate_max_len(v, 4000, "prompt")

    @field_validator("description", "summary")
    @classmethod
    def validate_text_fields(cls, v: Optional[str]) -> Optional[str]:
        """Validate text fields do not exceed 2000 characters."""
        return validate_max_len(v, 2000, "description/summary")

    @field_validator("tags", "custom_metadata", mode="before")
    @classmethod
    def validate_json_fields(cls, v: Any) -> Any:
        """Ensure JSON fields are serializable."""
        return validate_json_serializable(v)


class AssetMetadataCreateRequest(BaseModel):
    """Request model for creating asset metadata"""

    media_type: str = Field(..., description="Media type (image/video)")
    blob_name: str = Field(..., description="Asset name in Dataverse")
    container: str = Field(..., description="Dataverse container reference")
    url: str = Field(..., description="URL to access the asset")
    filename: str = Field(..., description="Original filename")
    size: int = Field(..., description="File size in bytes")
    content_type: Optional[str] = Field(None, description="MIME content type")
    folder_path: Optional[str] = Field("", description="Folder path in storage")

    # AI-generated content metadata
    prompt: Optional[str] = Field(None, description="Generation prompt")
    model: Optional[str] = Field(None, description="AI model used")
    generation_id: Optional[str] = Field(None, description="Generation job ID")

    # Analysis results
    summary: Optional[str] = Field(None, description="AI-generated summary")
    description: Optional[str] = Field(None, description="AI-generated description")
    products: Optional[str] = Field(None, description="Identified products/brands")
    tags: Optional[List[str]] = Field(None, description="Metadata tags")
    feedback: Optional[str] = Field(None, description="AI feedback")

    # Technical metadata
    quality: Optional[str] = Field(None, description="Generation quality setting")
    background: Optional[str] = Field(None, description="Background setting")
    output_format: Optional[str] = Field(None, description="Output format")
    has_transparency: Optional[bool] = Field(
        None, description="Has transparent background"
    )

    # Video-specific metadata
    duration: Optional[float] = Field(None, description="Video duration in seconds")
    fps: Optional[float] = Field(None, description="Frames per second")
    resolution: Optional[str] = Field(None, description="Video resolution")

    # Custom metadata
    custom_metadata: Optional[Dict[str, str]] = Field(
        None, description="Additional custom metadata"
    )


class AssetMetadataUpdateRequest(BaseModel):
    """Request model for updating asset metadata"""

    summary: Optional[str] = Field(None, description="AI-generated summary")
    description: Optional[str] = Field(None, description="AI-generated description")
    products: Optional[str] = Field(None, description="Identified products/brands")
    tags: Optional[List[str]] = Field(None, description="Metadata tags")
    feedback: Optional[str] = Field(None, description="AI feedback")
    folder_path: Optional[str] = Field(None, description="Folder path in storage")
    custom_metadata: Optional[Dict[str, str]] = Field(
        None, description="Additional custom metadata"
    )
    # NEW: Support nested analysis structure updates and analysis flag
    analysis: Optional[Dict[str, Any]] = Field(
        None, description="Nested analysis results structure"
    )
    has_analysis: Optional[bool] = Field(
        None, description="Flag indicating if analysis is available"
    )


class AssetMetadataResponse(BaseResponse):
    """Response model for asset metadata operations"""

    metadata: AssetMetadata = Field(..., description="Asset metadata")


class AssetMetadataListResponse(BaseResponse):
    """Response model for listing asset metadata"""

    items: List[AssetMetadata] = Field(..., description="List of asset metadata")
    total: int = Field(..., description="Total number of items")
    limit: int = Field(..., description="Number of items per page")
    offset: int = Field(..., description="Offset for pagination")
    has_more: bool = Field(..., description="Whether there are more items")


class AssetSearchRequest(BaseModel):
    """Request model for searching assets"""

    search_term: str = Field(..., description="Text to search for")
    media_type: Optional[str] = Field(None, description="Filter by media type")
    folder_path: Optional[str] = Field(None, description="Filter by folder path")
    tags: Optional[List[str]] = Field(None, description="Filter by tags")
    limit: int = Field(50, description="Maximum number of results", ge=1, le=100)
    offset: int = Field(0, description="Number of results to skip", ge=0)
    order_by: str = Field("created_at", description="Field to order by")
    order_desc: bool = Field(True, description="Order in descending order")


class AssetSearchResponse(BaseResponse):
    """Response model for asset search"""

    items: List[AssetMetadata] = Field(..., description="Search results")
    total: int = Field(..., description="Total number of results")
    limit: int = Field(..., description="Number of items per page")
    offset: int = Field(..., description="Offset for pagination")
    has_more: bool = Field(..., description="Whether there are more results")
    search_term: str = Field(..., description="The search term used")


class FolderStatsResponse(BaseResponse):
    """Response model for folder statistics"""

    folder_stats: List[Dict[str, Any]] = Field(..., description="Folder statistics")
    total_folders: int = Field(..., description="Total number of folders")


class RecentAssetsResponse(BaseResponse):
    """Response model for recent assets"""

    items: List[AssetMetadata] = Field(..., description="Recent assets")
    limit: int = Field(..., description="Number of items requested")


class MetadataSyncRequest(BaseModel):
    """Request model for syncing Dataverse metadata"""

    media_type: Optional[str] = Field(None, description="Sync specific media type only")
    force_update: bool = Field(False, description="Force update existing metadata")
    batch_size: int = Field(100, description="Batch size for processing", ge=1, le=1000)


class MetadataSyncResponse(BaseResponse):
    """Response model for metadata sync operation"""

    processed: int = Field(..., description="Number of items processed")
    created: int = Field(..., description="Number of new metadata records created")
    updated: int = Field(..., description="Number of existing records updated")
    errors: int = Field(..., description="Number of errors encountered")
    details: List[str] = Field(..., description="Detailed processing information")


# ============================================================================
# Asset Tag Models
# ============================================================================

class TagCategory(str, Enum):
    """Tag category enumeration (matches dystudio_TagCategory choice)."""
    STYLE = "100000000"
    SUBJECT = "100000001"
    COLOR = "100000002"
    MOOD = "100000003"
    BRAND = "100000004"
    OBJECT = "100000005"
    LOCATION = "100000006"


class MediaApplicability(str, Enum):
    """Media applicability enumeration (matches dystudio_MediaApplicability choice)."""
    IMAGE = "100000000"
    VIDEO = "100000001"
    BOTH = "100000002"


class AssetTag(BaseModel):
    """Asset tag model for Dataverse storage."""

    id: str = Field(..., description="Unique tag identifier (GUID)")
    name: str = Field(..., description="Tag name", max_length=200)
    tag_name: Optional[str] = Field(None, description="Alternate tag name", max_length=200)
    category: Optional[TagCategory] = Field(None, description="Tag category")
    description: Optional[str] = Field(None, description="Tag description", max_length=1000)
    usage_count: int = Field(default=0, description="Number of times tag has been used", ge=0)
    last_used: Optional[str] = Field(None, description="Last usage timestamp (ISO-8601)")
    media_applicability: MediaApplicability = Field(
        default=MediaApplicability.BOTH,
        description="Applicability to media types"
    )
    created_at: str = Field(..., description="Creation timestamp (ISO-8601)")
    updated_at: str = Field(..., description="Last update timestamp (ISO-8601)")

    @field_validator("created_at", "updated_at", "last_used")
    @classmethod
    def validate_tag_timestamps(cls, v: Optional[str]) -> Optional[str]:
        """Validate ISO-8601 timestamps."""
        return validate_iso_ts(v)

    @field_validator("name", "tag_name")
    @classmethod
    def validate_tag_names(cls, v: Optional[str]) -> Optional[str]:
        """Validate tag name length."""
        if v is None:
            return v
        return validate_max_len(v, 200, "tag name")

    @field_validator("description")
    @classmethod
    def validate_tag_description(cls, v: Optional[str]) -> Optional[str]:
        """Validate tag description length."""
        return validate_max_len(v, 1000, "tag description")


class AssetTagCreateRequest(BaseModel):
    """Request model for creating asset tags."""

    name: str = Field(..., description="Tag name", max_length=200)
    category: Optional[TagCategory] = Field(None, description="Tag category")
    description: Optional[str] = Field(None, description="Tag description", max_length=1000)
    media_applicability: MediaApplicability = Field(
        default=MediaApplicability.BOTH,
        description="Applicability to media types"
    )


class AssetTagResponse(BaseResponse):
    """Response model for asset tag operations."""

    tag: AssetTag = Field(..., description="Asset tag")


class AssetTagListResponse(BaseResponse):
    """Response model for listing asset tags."""

    items: List[AssetTag] = Field(..., description="List of asset tags")
    total: int = Field(..., description="Total number of tags")


# ============================================================================
# Generation History Models
# ============================================================================

class RequestType(str, Enum):
    """Request type enumeration (matches dystudio_RequestType choice)."""
    IMAGE = "100000000"
    VIDEO = "100000001"
    IMAGE_EDIT = "100000002"


class GenerationStatus(str, Enum):
    """Generation status enumeration (matches dystudio_GenerationStatus choice)."""
    PENDING = "100000000"
    IN_PROGRESS = "100000001"
    COMPLETED = "100000002"
    FAILED = "100000003"
    CANCELLED = "100000004"


class GenerationHistory(BaseModel):
    """Generation history model for Dataverse storage."""

    id: str = Field(..., description="Unique generation history identifier (GUID)")
    generation_id: str = Field(..., description="External generation ID", max_length=200)
    request_type: RequestType = Field(..., description="Type of generation request")
    prompt: str = Field(..., description="Generation prompt", max_length=4000)
    enhanced_prompt: Optional[str] = Field(None, description="Enhanced prompt", max_length=4000)
    model: str = Field(..., description="AI model used", max_length=200)
    parameters_json: Optional[str] = Field(None, description="Generation parameters (JSON)")
    status: GenerationStatus = Field(..., description="Current status")
    result_count: int = Field(default=0, description="Number of results generated", ge=0)
    started_at: str = Field(..., description="Start timestamp (ISO-8601)")
    completed_at: Optional[str] = Field(None, description="Completion timestamp (ISO-8601)")
    duration_ms: Optional[int] = Field(None, description="Duration in milliseconds", ge=0)
    tokens_used: Optional[int] = Field(None, description="Total tokens used", ge=0)
    input_tokens: Optional[int] = Field(None, description="Input tokens", ge=0)
    output_tokens: Optional[int] = Field(None, description="Output tokens", ge=0)
    estimated_cost: float = Field(default=0.0, description="Estimated cost in USD", ge=0.0)
    error_message: Optional[str] = Field(None, description="Error message if failed")
    created_at: str = Field(..., description="Creation timestamp (ISO-8601)")
    updated_at: str = Field(..., description="Last update timestamp (ISO-8601)")

    @field_validator("created_at", "updated_at", "started_at", "completed_at")
    @classmethod
    def validate_generation_timestamps(cls, v: Optional[str]) -> Optional[str]:
        """Validate ISO-8601 timestamps."""
        return validate_iso_ts(v)

    @field_validator("prompt", "enhanced_prompt")
    @classmethod
    def validate_generation_prompts(cls, v: Optional[str]) -> Optional[str]:
        """Validate prompt length."""
        return validate_max_len(v, 4000, "prompt")

    @field_validator("generation_id", "model")
    @classmethod
    def validate_generation_ids(cls, v: Optional[str]) -> Optional[str]:
        """Validate ID fields length."""
        if v is None:
            return v
        return validate_max_len(v, 200, "generation_id/model")

    @field_validator("parameters_json", mode="before")
    @classmethod
    def validate_parameters_json(cls, v: Any) -> Optional[str]:
        """Ensure parameters are JSON-serializable string."""
        if v is None:
            return v
        if isinstance(v, str):
            return v
        try:
            return json.dumps(v)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"parameters_json must be JSON-serializable: {exc}") from exc


class GenerationHistoryCreateRequest(BaseModel):
    """Request model for creating generation history."""

    generation_id: str = Field(..., description="External generation ID", max_length=200)
    request_type: RequestType = Field(..., description="Type of generation request")
    prompt: str = Field(..., description="Generation prompt", max_length=4000)
    enhanced_prompt: Optional[str] = Field(None, description="Enhanced prompt", max_length=4000)
    model: str = Field(..., description="AI model used", max_length=200)
    parameters: Optional[Dict[str, Any]] = Field(None, description="Generation parameters")
    started_at: Optional[str] = Field(None, description="Start timestamp (ISO-8601)")


class GenerationHistoryUpdateRequest(BaseModel):
    """Request model for updating generation history."""

    status: Optional[GenerationStatus] = Field(None, description="Updated status")
    result_count: Optional[int] = Field(None, description="Number of results", ge=0)
    completed_at: Optional[str] = Field(None, description="Completion timestamp (ISO-8601)")
    duration_ms: Optional[int] = Field(None, description="Duration in milliseconds", ge=0)
    tokens_used: Optional[int] = Field(None, description="Total tokens used", ge=0)
    input_tokens: Optional[int] = Field(None, description="Input tokens", ge=0)
    output_tokens: Optional[int] = Field(None, description="Output tokens", ge=0)
    estimated_cost: Optional[float] = Field(None, description="Estimated cost in USD", ge=0.0)
    error_message: Optional[str] = Field(None, description="Error message if failed")


class GenerationHistoryResponse(BaseResponse):
    """Response model for generation history operations."""

    generation: GenerationHistory = Field(..., description="Generation history record")


class GenerationHistoryListResponse(BaseResponse):
    """Response model for listing generation history."""

    items: List[GenerationHistory] = Field(..., description="List of generation history records")
    total: int = Field(..., description="Total number of records")
