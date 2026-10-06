"""
Gallery API endpoints using Dataverse as the sole storage and metadata system.
Images are stored as Dataverse file attachments with metadata records.
"""

from fastapi import (
    APIRouter,
    HTTPException,
    Depends,
    Query,
    UploadFile,
    File,
    Form,
    Body,
)
from typing import Dict, List, Optional, Any
from fastapi.responses import Response
import io
import os
import logging
import base64
from datetime import datetime, timezone
from PIL import Image

from backend.core.dataverse_service import (
    DataverseService,
    DataverseError,
    DataverseAuthenticationError,
    DataverseRecordNotFoundError,
)
from backend.core.config import settings
from backend.models.gallery import (
    GalleryResponse,
    GalleryItem,
    MediaType,
    AssetUploadResponse,
    AssetDeleteResponse,
    AssetUrlResponse,
    AssetMetadataResponse,
    MetadataUpdateRequest,
)
from backend.models.metadata_models import AssetMetadataCreateRequest

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter()


def get_dataverse_service() -> DataverseService:
    """Dependency to get Dataverse service instance (required)"""
    try:
        return DataverseService()
    except Exception as e:
        logger.error(f"Failed to initialize Dataverse service: {e}")
        raise HTTPException(status_code=503, detail="Dataverse service unavailable")


def _build_gallery_item(metadata: Dict[str, Any]) -> GalleryItem:
    """Convert Dataverse metadata into a gallery item."""
    asset_id = metadata.get("id")
    if not asset_id:
        raise ValueError("Asset metadata missing id")

    media_type_value = metadata.get("media_type") or "image"
    media_type_str = str(media_type_value).lower()
    try:
        media_type_enum = MediaType(media_type_value)
    except ValueError:
        media_type_enum = MediaType.VIDEO if "video" in media_type_str else MediaType.IMAGE

    name = metadata.get("filename") or metadata.get("blob_name") or str(asset_id)
    container = metadata.get("container") or "dataverse"

    size_value = metadata.get("size")
    if isinstance(size_value, str):
        try:
            size = int(size_value)
        except ValueError:
            size = 0
    elif size_value is None:
        size = 0
    else:
        size = int(size_value)

    creation_time = metadata.get("created_at")
    if not creation_time:
        creation_time = datetime.now(timezone.utc).isoformat()
    last_modified = metadata.get("updated_at") or creation_time
    folder_path = metadata.get("folder_path") or ""

    details: Dict[str, Any] = {}

    def add_detail(key: str, value: Any) -> None:
        if value is not None:
            details[key] = value

    add_detail("prompt", metadata.get("prompt"))
    add_detail("model", metadata.get("model"))
    add_detail("quality", metadata.get("quality"))
    add_detail("background", metadata.get("background"))
    add_detail("output_format", metadata.get("output_format"))
    add_detail("has_transparency", metadata.get("has_transparency"))
    add_detail("width", metadata.get("width"))
    add_detail("height", metadata.get("height"))
    add_detail("description", metadata.get("description"))
    add_detail("analysis", metadata.get("analysis"))
    add_detail("has_analysis", metadata.get("has_analysis"))
    add_detail("custom_metadata", metadata.get("custom_metadata"))
    add_detail("source_url", metadata.get("url"))

    if media_type_enum == MediaType.VIDEO:
        add_detail("duration", metadata.get("duration"))
        add_detail("fps", metadata.get("fps"))
        add_detail("resolution", metadata.get("resolution"))

    tags = metadata.get("tags")
    if tags:
        details["tags"] = tags

    analysis = metadata.get("analysis")
    if isinstance(analysis, dict):
        summary = analysis.get("summary")
        if summary:
            details.setdefault("summary", summary)
        analysis_tags = analysis.get("tags")
        if analysis_tags:
            details.setdefault("analysis_tags", analysis_tags)
    else:
        summary = metadata.get("summary")
        if summary:
            details.setdefault("summary", summary)

    content_type = metadata.get("content_type") or "image/png"
    data_url = f"/api/v1/gallery/assets/{asset_id}/content"

    # Support older records that stored inline base64 data
    image_data_b64 = metadata.get("image_data")
    if image_data_b64:
        try:
            data_url = f"data:{content_type};base64,{image_data_b64}"
        except Exception:
            logger.debug("Failed to build data URL from inline image_data; falling back to content endpoint")
            data_url = f"/api/v1/gallery/assets/{asset_id}/content"

    return GalleryItem(
        id=str(asset_id),
        name=name,
        media_type=media_type_enum,
        url=data_url,
        container=container,
        size=size,
        content_type=content_type,
        creation_time=creation_time,
        last_modified=last_modified,
        metadata=details or None,
        folder_path=folder_path,
    )


@router.get("/images", response_model=GalleryResponse)
async def get_gallery_images(
    limit: int = Query(
        50, description="Maximum number of items to return", ge=1, le=100
    ),
    offset: int = Query(0, description="Offset for pagination"),
    folder_path: Optional[str] = Query(
        None, description="Optional folder path to filter assets"
    ),
    tags: Optional[str] = Query(
        None, description="Comma-separated tags to filter by"
    ),
    dataverse_service: DataverseService = Depends(get_dataverse_service),
):
    """Get gallery images from Dataverse"""
    try:
        # Parse tags if provided
        tag_list = None
        if tags:
            tag_list = [tag.strip() for tag in tags.split(',') if tag.strip()]

        # Query images from Dataverse
        result = dataverse_service.query_assets(
            media_type="image",
            folder_path=folder_path,
            tags=tag_list,
            limit=limit,
            offset=offset,
            order_by="createdon",
            order_desc=True
        )

        items = []
        for metadata in result.get("items", []):
            try:
                item = _build_gallery_item(metadata)
                if item.media_type != MediaType.IMAGE:
                    continue
                items.append(item)
            except Exception as exc:
                logger.warning(f"Skipping gallery item due to invalid metadata: {exc}")

        return GalleryResponse(
            items=items,
            total=result.get("total", len(items)),
            limit=limit,
            offset=offset,
            continuation_token=None,
            has_more=result.get("has_more", False),
        )

    except DataverseError as e:
        logger.error(f"Dataverse error: {type(e).__name__}: {e}", exc_info=True)
        raise HTTPException(status_code=503, detail=f"Dataverse service error: {str(e)}")
    except Exception as e:
        logger.error(f"Error retrieving images: {type(e).__name__}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to retrieve images: {str(e)}")


@router.get("/videos", response_model=GalleryResponse)
async def get_gallery_videos(
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0),
    folder_path: Optional[str] = Query(None),
    dataverse_service: DataverseService = Depends(get_dataverse_service),
):
    """Get gallery videos from Dataverse"""
    try:
        result = dataverse_service.query_assets(
            media_type="video",
            folder_path=folder_path,
            limit=limit,
            offset=offset,
            order_by="createdon",
            order_desc=True
        )

        items = []
        for metadata in result.get("items", []):
            try:
                item = _build_gallery_item(metadata)
                if item.media_type != MediaType.VIDEO:
                    continue
                items.append(item)
            except Exception as exc:
                logger.warning(f"Skipping gallery item due to invalid metadata: {exc}")

        return GalleryResponse(
            items=items,
            total=result.get("total", len(items)),
            limit=limit,
            offset=offset,
            continuation_token=None,
            has_more=result.get("has_more", False),
        )

    except DataverseError as e:
        logger.error(f"Dataverse error: {e}")
        raise HTTPException(status_code=503, detail="Dataverse service error")
    except Exception as e:
        logger.error(f"Error retrieving videos: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve videos")


@router.get("/assets/{asset_id}/content")
async def get_asset_content(
    asset_id: str,
    size: Optional[str] = Query(None, description="Optional size: thumbnail, medium, full"),
    dataverse_service: DataverseService = Depends(get_dataverse_service),
):
    """Get asset content directly from Dataverse"""
    try:
        # Get asset metadata including image data
        asset_metadata = dataverse_service.get_asset_metadata(asset_id)
        if not asset_metadata:
            raise HTTPException(status_code=404, detail="Asset not found")

        # If asset uses local fallback storage, serve the local file
        container = asset_metadata.get("container")
        url = asset_metadata.get("url") or ""
        if container == "local" or (isinstance(url, str) and url.startswith(f"/{settings.IMAGE_DIR.rstrip('/')}")):
            # Resolve local file path
            # url is like /static/images/<filename>
            try:
                local_path = url.lstrip("/")
                # Ensure path is inside configured image dir
                base_dir = os.path.abspath(settings.IMAGE_DIR)
                candidate = os.path.abspath(local_path)
                if not candidate.startswith(base_dir):
                    logger.error(f"Attempt to access file outside image dir: {candidate}")
                    raise HTTPException(status_code=404, detail="Asset content not found")
                with open(candidate, "rb") as f:
                    image_bytes = f.read()
                content_type = asset_metadata.get("content_type", "image/png")
                return Response(
                    content=image_bytes,
                    media_type=content_type,
                    headers={
                        "Cache-Control": "public, max-age=3600",
                        "Content-Length": str(len(image_bytes))
                    }
                )
            except FileNotFoundError:
                raise HTTPException(status_code=404, detail="Asset content not found")
            except HTTPException:
                raise
            except Exception as e:
                logger.error(f"Failed to serve local asset file: {e}")
                raise HTTPException(status_code=500, detail="Failed to retrieve asset content")

        image_bytes: Optional[bytes] = None
        content_type = asset_metadata.get("content_type", "image/png")

        if container == "dataverse":
            try:
                file_bytes, file_content_type, _ = dataverse_service.download_asset_file(asset_id)
                if file_bytes:
                    image_bytes = file_bytes
                    if file_content_type:
                        content_type = file_content_type
            except DataverseRecordNotFoundError:
                logger.warning(f"No file attachment found for asset {asset_id}; checking inline data")
            except DataverseError as e:
                logger.error(f"Failed to download file for asset {asset_id}: {e}")
                raise HTTPException(status_code=503, detail="Dataverse service error")

        if image_bytes is None:
            image_data_b64 = asset_metadata.get("image_data")
            if not image_data_b64:
                raise HTTPException(status_code=404, detail="Asset content not found")
            try:
                image_bytes = base64.b64decode(image_data_b64)
            except Exception as e:
                logger.error(f"Failed to decode image data for asset {asset_id}: {e}")
                raise HTTPException(status_code=500, detail="Failed to decode asset content")

        # Process size if requested
        if size == "thumbnail":
            try:
                with Image.open(io.BytesIO(image_bytes)) as img:
                    img.thumbnail((200, 200), Image.Resampling.LANCZOS)
                    output = io.BytesIO()
                    img_format = img.format if img.format else "PNG"
                    img.save(output, format=img_format)
                    image_bytes = output.getvalue()
            except Exception as e:
                logger.warning(f"Failed to create thumbnail for {asset_id}: {e}")
                # Return original if thumbnail creation fails

        elif size == "medium":
            try:
                with Image.open(io.BytesIO(image_bytes)) as img:
                    img.thumbnail((800, 600), Image.Resampling.LANCZOS)
                    output = io.BytesIO()
                    img_format = img.format if img.format else "PNG"
                    img.save(output, format=img_format)
                    image_bytes = output.getvalue()
            except Exception as e:
                logger.warning(f"Failed to create medium size for {asset_id}: {e}")

        # Determine content type
        return Response(
            content=image_bytes,
            media_type=content_type,
            headers={
                "Cache-Control": "public, max-age=3600",
                "Content-Length": str(len(image_bytes))
            }
        )

    except HTTPException:
        raise
    except DataverseError as e:
        logger.error(f"Dataverse error getting asset content: {e}")
        raise HTTPException(status_code=503, detail="Dataverse service error")
    except Exception as e:
        logger.error(f"Error getting asset content: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve asset content")


@router.post("/upload", response_model=AssetUploadResponse)
async def upload_asset(
    file: UploadFile = File(...),
    media_type: MediaType = Form(...),
    folder_path: Optional[str] = Form(None),
    dataverse_service: DataverseService = Depends(get_dataverse_service),
):
    """Upload an asset directly to Dataverse"""
    try:
        # Read file content
        file_content = await file.read()

        # Get file info
        file_size = len(file_content)
        content_type = file.content_type or "application/octet-stream"
        
        # Get dimensions for images
        width, height = None, None
        if media_type == MediaType.IMAGE:
            try:
                with Image.open(io.BytesIO(file_content)) as img:
                    width, height = img.size
            except Exception as e:
                logger.warning(f"Failed to get image dimensions: {e}")

        # Create metadata for Dataverse
        metadata = {
            "media_type": media_type.value,
            "blob_name": file.filename,  # For compatibility
            "container": "dataverse",
            "filename": file.filename,
            "size": file_size,
            "content_type": content_type,
            "folder_path": folder_path,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        
        if width and height:
            metadata.update({"width": width, "height": height})

        # Store in Dataverse
        try:
            metadata_record = dataverse_service.create_asset_metadata(metadata)
        except DataverseError as e:
            logger.error(f"Dataverse error creating asset metadata: {e}")
            raise HTTPException(status_code=503, detail="Dataverse service error")

        asset_id = metadata_record.get("id")
        if not asset_id:
            raise HTTPException(status_code=500, detail="Dataverse did not return an asset identifier")

        try:
            dataverse_service.upload_asset_file(
                asset_id,
                file_content,
                filename=file.filename,
                content_type=content_type,
            )
            try:
                dataverse_service.update_asset_metadata(asset_id, {"url": f"dataverse://{asset_id}"})
            except DataverseError as update_exc:
                logger.debug(f"Failed to update asset {asset_id} URL metadata: {update_exc}")
        except DataverseError as e:
            msg = str(e)
            logger.warning(f"Dataverse error uploading file content: {msg}. Falling back to local file storage.")

            image_dir = os.path.abspath(settings.IMAGE_DIR)
            os.makedirs(image_dir, exist_ok=True)

            _, ext = os.path.splitext(file.filename or "")
            ext = ext or ".png"
            local_filename = f"{asset_id}{ext}"
            local_path = os.path.join(image_dir, local_filename)

            try:
                with open(local_path, "wb") as f:
                    f.write(file_content)
            except Exception as write_exc:
                logger.error(f"Failed to write fallback file to {local_path}: {write_exc}")
                raise HTTPException(status_code=500, detail="Failed to store asset")

            try:
                dataverse_service.update_asset_metadata(
                    asset_id,
                    {
                        "container": "local",
                        "url": f"/{settings.IMAGE_DIR.rstrip('/')}/{local_filename}",
                        "blob_name": local_filename,
                    },
                )
            except DataverseError as update_exc:
                logger.debug(f"Failed to update fallback metadata for asset {asset_id}: {update_exc}")

            return AssetUploadResponse(
                success=True,
                message="Asset uploaded with local fallback storage",
                asset_id=asset_id,
                url=f"/{settings.IMAGE_DIR.rstrip('/')}/{local_filename}",
                size=file_size,
            )

        return AssetUploadResponse(
            success=True,
            message="Asset uploaded successfully",
            asset_id=asset_id,
            url=f"/api/v1/gallery/assets/{asset_id}/content",
            size=file_size,
        )

    except DataverseError as e:
        logger.error(f"Dataverse error uploading asset: {e}")
        raise HTTPException(status_code=503, detail="Dataverse service error")
    except Exception as e:
        logger.error(f"Error uploading asset: {e}")
        raise HTTPException(status_code=500, detail="Failed to upload asset")


@router.delete("/assets/{asset_id}", response_model=AssetDeleteResponse)
async def delete_asset(
    asset_id: str,
    dataverse_service: DataverseService = Depends(get_dataverse_service),
):
    """Delete an asset from Dataverse"""
    try:
        metadata = dataverse_service.get_asset_metadata(asset_id)
        blob_name = metadata.get("blob_name") if metadata else None
        container = metadata.get("container") if metadata else None

        success = dataverse_service.delete_asset_metadata(asset_id)

        if success:
            logger.info(f"Successfully deleted asset {asset_id}")
            return AssetDeleteResponse(
                success=True,
                message="Asset deleted successfully",
                blob_name=blob_name,
                container=container
            )
        else:
            raise HTTPException(status_code=404, detail="Asset not found")

    except DataverseError as e:
        logger.error(f"Dataverse error deleting asset: {e}")
        raise HTTPException(status_code=503, detail="Dataverse service error")
    except Exception as e:
        logger.error(f"Error deleting asset: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete asset")


@router.get("/search")
async def search_assets(
    query: str = Query(..., description="Search query"),
    media_type: Optional[str] = Query(None, description="Filter by media type"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0),
    dataverse_service: DataverseService = Depends(get_dataverse_service),
):
    """Search assets in Dataverse"""
    try:
        result = dataverse_service.search_assets(
            search_term=query,
            media_type=media_type,
            limit=limit,
            offset=offset
        )

        items = []
        for metadata in result.get("items", []):
            try:
                items.append(_build_gallery_item(metadata))
            except Exception as exc:
                logger.warning(f"Skipping gallery item due to invalid metadata: {exc}")

        return GalleryResponse(
            items=items,
            total=result.get("total", len(items)),
            limit=limit,
            offset=offset,
            continuation_token=None,
            has_more=result.get("has_more", False),
        )

    except DataverseError as e:
        logger.error(f"Dataverse error searching assets: {e}")
        raise HTTPException(status_code=503, detail="Dataverse service error")
    except Exception as e:
        logger.error(f"Error searching assets: {e}")
        raise HTTPException(status_code=500, detail="Failed to search assets")


@router.get("/folders")
async def get_folders(
    media_type: Optional[str] = Query(None, description="Filter by media type (image or video)"),
    dataverse_service: DataverseService = Depends(get_dataverse_service),
):
    """Get all folders from Dataverse"""
    try:
        result = dataverse_service.get_all_folders(media_type=media_type)
        return {
            "folders": result["folders"],
            "total": result["total_folders"]
        }

    except DataverseError as e:
        logger.error(f"Dataverse error getting folders: {type(e).__name__}: {e}", exc_info=True)
        raise HTTPException(status_code=503, detail=f"Dataverse service error: {str(e)}")
    except Exception as e:
        logger.error(f"Error getting folders: {type(e).__name__}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to retrieve folders: {str(e)}")


@router.get("/health")
async def gallery_health_check(
    dataverse_service: DataverseService = Depends(get_dataverse_service),
):
    """Health check for gallery service"""
    try:
        health_status = {
            "status": "healthy",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "services": {}
        }

        # Check Dataverse
        try:
            dataverse_health = dataverse_service.health_check()
            health_status["services"]["dataverse"] = dataverse_health
            
            if dataverse_health["status"] != "healthy":
                health_status["status"] = "degraded"
                
        except Exception as e:
            health_status["services"]["dataverse"] = {
                "status": "unhealthy",
                "error": str(e),
                "message": "Dataverse service unavailable",
            }
            health_status["status"] = "unhealthy"

        return health_status

    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {
            "status": "unhealthy",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "error": str(e)
        }
