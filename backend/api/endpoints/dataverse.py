"""
Dataverse integration endpoints for Vision Design prototype.
Provides rich metadata storage and querying capabilities.
"""

from fastapi import APIRouter, HTTPException
from typing import Dict, List, Any, Optional
from pydantic import BaseModel
import logging
from backend.core.dataverse_client import get_dataverse_client

logger = logging.getLogger(__name__)

router = APIRouter()


class ImageMetadataRequest(BaseModel):
    """Request model for storing image metadata in Dataverse"""
    filename: str
    prompt: str
    model: str
    url: str
    file_hash: Optional[str] = None
    width: Optional[int] = None
    height: Optional[int] = None
    file_size: Optional[int] = None
    tags: Optional[List[str]] = []
    quality: Optional[str] = None
    seed: Optional[int] = None
    model_version: Optional[str] = None
    generation_settings: Optional[Dict[str, Any]] = {}


class ImageQueryRequest(BaseModel):
    """Request model for querying images from Dataverse"""
    model: Optional[str] = None
    prompt_contains: Optional[str] = None
    date_from: Optional[str] = None
    date_to: Optional[str] = None
    limit: Optional[int] = 100


class TagUpdateRequest(BaseModel):
    """Request model for updating image tags"""
    tags: List[str]


@router.post("/dataverse/images")
async def store_image_metadata(request: ImageMetadataRequest) -> Dict[str, Any]:
    """
    Store image metadata in Dataverse
    
    Args:
        request: Image metadata to store
        
    Returns:
        Dictionary with success status and record ID
    """
    try:
        dataverse_client = get_dataverse_client()
        
        if not dataverse_client or not dataverse_client.enabled:
            raise HTTPException(
                status_code=503,
                detail="Dataverse service is not available or not configured"
            )
        
        # Convert request to metadata dictionary
        metadata = request.dict()
        
        # Store in Dataverse
        record_id = dataverse_client.store_image_metadata(metadata)
        
        if record_id:
            return {
                "success": True,
                "record_id": record_id,
                "message": "Image metadata stored successfully"
            }
        else:
            raise HTTPException(
                status_code=500,
                detail="Failed to store image metadata in Dataverse"
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error storing image metadata: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Internal error: {str(e)}"
        )


@router.post("/dataverse/images/query")
async def query_images(request: ImageQueryRequest) -> Dict[str, Any]:
    """
    Query images from Dataverse with optional filtering
    
    Args:
        request: Query parameters
        
    Returns:
        Dictionary with query results
    """
    try:
        dataverse_client = get_dataverse_client()
        
        if not dataverse_client or not dataverse_client.enabled:
            raise HTTPException(
                status_code=503,
                detail="Dataverse service is not available or not configured"
            )
        
        # Build filter parameters
        filter_params = {}
        if request.model:
            filter_params["model"] = request.model
        if request.prompt_contains:
            filter_params["prompt_contains"] = request.prompt_contains
        if request.date_from:
            filter_params["date_from"] = request.date_from
        if request.date_to:
            filter_params["date_to"] = request.date_to
        
        # Query images
        results = dataverse_client.query_images(
            filter_params=filter_params,
            limit=request.limit or 100
        )
        
        return {
            "success": True,
            "images": results,
            "count": len(results)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error querying images: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Internal error: {str(e)}"
        )


@router.put("/dataverse/images/{record_id}/tags")
async def update_image_tags(record_id: str, request: TagUpdateRequest) -> Dict[str, Any]:
    """
    Update tags for an image record
    
    Args:
        record_id: Dataverse record ID
        request: Tags to update
        
    Returns:
        Dictionary with success status
    """
    try:
        dataverse_client = get_dataverse_client()
        
        if not dataverse_client or not dataverse_client.enabled:
            raise HTTPException(
                status_code=503,
                detail="Dataverse service is not available or not configured"
            )
        
        # Update tags
        success = dataverse_client.update_image_tags(record_id, request.tags)
        
        if success:
            return {
                "success": True,
                "message": "Tags updated successfully"
            }
        else:
            raise HTTPException(
                status_code=500,
                detail="Failed to update tags"
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating tags: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Internal error: {str(e)}"
        )


@router.delete("/dataverse/images/{record_id}")
async def delete_image_record(record_id: str) -> Dict[str, Any]:
    """
    Delete an image record from Dataverse
    
    Args:
        record_id: Dataverse record ID
        
    Returns:
        Dictionary with success status
    """
    try:
        dataverse_client = get_dataverse_client()
        
        if not dataverse_client or not dataverse_client.enabled:
            raise HTTPException(
                status_code=503,
                detail="Dataverse service is not available or not configured"
            )
        
        # Delete record
        success = dataverse_client.delete_image_record(record_id)
        
        if success:
            return {
                "success": True,
                "message": "Record deleted successfully"
            }
        else:
            raise HTTPException(
                status_code=500,
                detail="Failed to delete record"
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting record: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Internal error: {str(e)}"
        )


@router.get("/dataverse/status")
async def get_dataverse_status() -> Dict[str, Any]:
    """
    Get Dataverse connection status
    
    Returns:
        Dictionary with connection status and configuration info
    """
    try:
        dataverse_client = get_dataverse_client()
        
        if not dataverse_client:
            return {
                "enabled": False,
                "configured": False,
                "message": "Dataverse client not initialized"
            }
        
        return {
            "enabled": dataverse_client.enabled,
            "configured": bool(dataverse_client.environment_url),
            "environment_url": dataverse_client.environment_url,
            "table_name": dataverse_client.table_name,
            "message": "Dataverse is available" if dataverse_client.enabled else "Dataverse is not properly configured"
        }
        
    except Exception as e:
        logger.error(f"Error getting Dataverse status: {e}")
        return {
            "enabled": False,
            "configured": False,
            "error": str(e),
            "message": "Error checking Dataverse status"
        }