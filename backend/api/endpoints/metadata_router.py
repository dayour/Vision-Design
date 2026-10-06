"""FastAPI router exposing Dataverse-backed metadata endpoints."""

from fastapi import APIRouter, HTTPException, Depends, Query, Body, BackgroundTasks
from typing import Dict, List, Optional, Any
import logging

from backend.core.dataverse_service import (
    DataverseService,
    DataverseError,
    DataverseAuthenticationError,
    DataverseRecordNotFoundError,
    DataverseQuotaExceededError,
)
from backend.core.config import settings
from backend.models.metadata_models import (
    AssetMetadata,
    AssetMetadataCreateRequest,
    AssetMetadataUpdateRequest,
    AssetMetadataResponse,
    AssetMetadataListResponse,
    AssetSearchRequest,
    AssetSearchResponse,
    FolderStatsResponse,
    RecentAssetsResponse,
    MetadataSyncRequest,
    MetadataSyncResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter()


def get_dataverse_service() -> DataverseService:
    """Dependency to get Dataverse service instance (required)"""
    try:
        return DataverseService()
    except Exception as e:
        logger.error(f"Failed to initialize Dataverse service: {e}")
        raise HTTPException(status_code=503, detail="Dataverse service unavailable")


@router.post("/", response_model=AssetMetadataResponse)
async def create_asset_metadata(
    request: AssetMetadataCreateRequest = Body(...),
    dataverse_service: DataverseService = Depends(get_dataverse_service),
) -> AssetMetadataResponse:
    """Create a new asset metadata record in Dataverse."""
    try:
        metadata_dict = request.model_dump() if hasattr(request, "model_dump") else request.dict()
        record_id = dataverse_service.create_asset_metadata(metadata_dict)
        
        if not record_id:
            raise HTTPException(status_code=500, detail="Failed to create metadata record")
            
        record = dataverse_service.get_asset_metadata(record_id)
        return AssetMetadataResponse(success=True, message="Created", metadata=AssetMetadata(**record))
        
    except DataverseError as e:
        logger.error(f"Dataverse error creating metadata: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        logger.error(f"Error creating metadata: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{asset_id}", response_model=AssetMetadataResponse)
async def get_asset_metadata(
    asset_id: str,
    dataverse_service: DataverseService = Depends(get_dataverse_service),
) -> AssetMetadataResponse:
    """Retrieve a single asset metadata record by ID."""
    try:
        record = dataverse_service.get_asset_metadata(asset_id)
        if not record:
            raise HTTPException(status_code=404, detail="Asset metadata not found")
        return AssetMetadataResponse(success=True, message="Found", metadata=AssetMetadata(**record))
    except DataverseRecordNotFoundError:
        raise HTTPException(status_code=404, detail="Asset metadata not found")
    except Exception as e:
        logger.error(f"Error retrieving metadata for {asset_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{asset_id}", response_model=AssetMetadataResponse)
async def update_asset_metadata(
    asset_id: str,
    request: AssetMetadataUpdateRequest = Body(...),
    dataverse_service: DataverseService = Depends(get_dataverse_service),
) -> AssetMetadataResponse:
    """Update an existing asset metadata record."""
    try:
        # Get existing record first to check if it exists
        existing = dataverse_service.get_asset_metadata(asset_id)
        if not existing:
            raise HTTPException(status_code=404, detail="Asset metadata not found")
        
        # Extract updates from request
        updates = request.model_dump(exclude_unset=True) if hasattr(request, "model_dump") else request.dict(exclude_unset=True)
        
        if not updates:
            return AssetMetadataResponse(success=True, message="No changes supplied", metadata=AssetMetadata(**existing))
        
        # Update the record
        existing_media_type = existing.get("media_type") if isinstance(existing, dict) else None
        updated = dataverse_service.update_asset_metadata(asset_id, updates, existing_media_type)
        if not updated:
            raise HTTPException(status_code=404, detail="Asset metadata not found or not updated")
            
        # Get the updated record to return
        record = dataverse_service.get_asset_metadata(asset_id)
        return AssetMetadataResponse(success=True, message="Updated", metadata=AssetMetadata(**record))
        
    except DataverseRecordNotFoundError:
        raise HTTPException(status_code=404, detail="Asset metadata not found")
    except DataverseError as e:
        logger.error(f"Dataverse error updating metadata: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        logger.error(f"Error updating metadata for {asset_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{asset_id}")
async def delete_asset_metadata(
    asset_id: str,
    dataverse_service: DataverseService = Depends(get_dataverse_service),
) -> Dict[str, Any]:
    """Delete an asset metadata record."""
    try:
        deleted = dataverse_service.delete_asset_metadata(asset_id)
        if not deleted:
            raise HTTPException(status_code=404, detail="Asset metadata not found")
        return {"success": True, "message": "Deleted"}
    except DataverseRecordNotFoundError:
        raise HTTPException(status_code=404, detail="Asset metadata not found")
    except DataverseError as e:
        logger.error(f"Dataverse error deleting metadata: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        logger.error(f"Error deleting metadata for {asset_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/list", response_model=AssetMetadataListResponse)
async def list_asset_metadata(
    limit: int = Query(50, description='Maximum number of results', ge=1, le=100),
    offset: int = Query(0, description='Offset for pagination', ge=0),
    media_type: Optional[str] = Query(None, description='Filter by media type'),
    folder_path: Optional[str] = Query(None, description='Filter by folder path'),
    dataverse_service: DataverseService = Depends(get_dataverse_service),
) -> AssetMetadataListResponse:
    """List asset metadata with pagination and filtering."""
    try:
        result = dataverse_service.list_asset_metadata(
            limit=limit,
            offset=offset,
            media_type=media_type,
            folder_path=folder_path,
        )
        metadata_items = [AssetMetadata(**item) for item in result.get('items', [])]
        return AssetMetadataListResponse(
            success=True,
            message='Asset metadata list retrieved successfully',
            items=metadata_items,
            total=result.get('total', len(metadata_items)),
            limit=result.get('limit', limit),
            offset=result.get('offset', offset),
            has_more=result.get('has_more', False),
        )
    except DataverseQuotaExceededError as exc:
        logger.warning('Dataverse quota exceeded while listing metadata: %s', exc)
        raise HTTPException(status_code=429, detail=str(exc)) from exc
    except DataverseAuthenticationError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc
    except Exception as exc:
        logger.error('Error listing asset metadata: %s', exc)
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/search", response_model=AssetSearchResponse)
async def search_asset_metadata(
    request: AssetSearchRequest,
    dataverse_service: DataverseService = Depends(get_dataverse_service),
) -> AssetSearchResponse:
    """Search asset metadata by text or structured filters."""
    try:
        if request.search_term:
            result = dataverse_service.search_assets(
                search_term=request.search_term,
                media_type=request.media_type,
                folder_path=request.folder_path,
                tags=request.tags,
                limit=request.limit,
                offset=request.offset,
            )
        else:
            result = dataverse_service.query_assets(
                media_type=request.media_type,
                folder_path=request.folder_path,
                tags=request.tags,
                limit=request.limit,
                offset=request.offset,
                order_by=request.order_by,
                order_desc=request.order_desc,
            )
        metadata_items = [AssetMetadata(**item) for item in result.get('items', [])]
        return AssetSearchResponse(
            success=True,
            message='Search completed successfully',
            items=metadata_items,
            total=result.get('total', len(metadata_items)),
            limit=result.get('limit', request.limit),
            offset=result.get('offset', request.offset),
            has_more=result.get('has_more', False),
            search_term=request.search_term,
        )
    except DataverseQuotaExceededError as exc:
        logger.warning('Dataverse quota exceeded during asset search: %s', exc)
        raise HTTPException(status_code=429, detail=str(exc)) from exc
    except DataverseAuthenticationError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc
    except Exception as exc:
        logger.error('Error searching asset metadata: %s', exc)
        raise HTTPException(status_code=500, detail=str(exc)) from exc
@router.get("/stats/folders", response_model=FolderStatsResponse)
async def get_folder_statistics(
    media_type: Optional[str] = Query(None, description="Filter by media type"),
    dataverse_service: DataverseService = Depends(get_dataverse_service),
) -> FolderStatsResponse:
    """Get folder usage statistics"""
    try:
        stats = dataverse_service.get_folder_stats(media_type=media_type)

        return FolderStatsResponse(
            success=True,
            message="Folder statistics retrieved successfully",
            folder_stats=stats["folder_stats"],
            total_folders=stats["total_folders"],
        )
    except Exception as e:
        logger.error(f"Error getting folder statistics: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/recent", response_model=RecentAssetsResponse)
async def get_recent_assets(
    media_type: Optional[str] = Query(None, description="Filter by media type"),
    limit: int = Query(20, description="Maximum number of results", ge=1, le=100),
    dataverse_service: DataverseService = Depends(get_dataverse_service),
) -> RecentAssetsResponse:
    """Get recently created assets"""
    try:
        items = dataverse_service.get_recent_assets(media_type=media_type, limit=limit)

        # Convert items to AssetMetadata objects
        metadata_items = [AssetMetadata(**item) for item in items]

        return RecentAssetsResponse(
            success=True,
            message="Recent assets retrieved successfully",
            items=metadata_items,
            limit=limit,
        )
    except Exception as e:
        logger.error(f"Error getting recent assets: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


async def _sync_metadata_background(
    sync_request: MetadataSyncRequest,
    dataverse_service: DataverseService,
) -> MetadataSyncResponse:
    """Background task to sync Dataverse metadata.

    This repository uses Dataverse as the authoritative metadata store. The
    sync routine is intentionally a no-op that records intent and exits.
    """
    processed = 0
    created = 0
    updated = 0
    errors = 0
    details: List[str] = []

    try:
        logger.info("Metadata sync invoked (no-op for Dataverse-backed storage)")
        details.append("No-op: Dataverse is authoritative for metadata")
        return MetadataSyncResponse(
            success=True,
            message="No-op: Dataverse is authoritative for metadata",
            processed=processed,
            created=created,
            updated=updated,
            errors=errors,
            details=details,
        )
    except Exception as e:
        logger.exception("Unexpected error in metadata sync background task")
        return MetadataSyncResponse(
            success=False,
            message="Metadata sync failed",
            processed=processed,
            created=created,
            updated=updated,
            errors=errors + 1,
            details=[f"Error: {str(e)}"],
        )


@router.post("/sync", response_model=MetadataSyncResponse)
async def sync_metadata(
    background_tasks: BackgroundTasks,
    request: MetadataSyncRequest,
    dataverse_service: DataverseService = Depends(get_dataverse_service),
) -> MetadataSyncResponse:
    """Start a background metadata sync task (no-op for Dataverse-only storage)."""
    try:
        background_tasks.add_task(_sync_metadata_background, request, dataverse_service)
        return MetadataSyncResponse(
            success=True,
            message="Metadata sync queued (no-op for Dataverse-only storage)",
            processed=0,
            created=0,
            updated=0,
            errors=0,
            details=["Sync task queued (no-op)"],
        )
    except Exception as e:
        logger.exception("Failed to queue metadata sync task")
        raise HTTPException(status_code=500, detail=str(e))
