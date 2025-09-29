from fastapi import APIRouter, HTTPException
from typing import Dict, Any
import logging
import base64
import io
from PIL import Image

from backend.models.images import (
    FluxGenerationRequest,
    FluxEditRequest,
    ImageGenerationResponse
)
from backend.core.flux_client import FluxClient
from backend.core.config import settings

# Set up logging
logger = logging.getLogger(__name__)

router = APIRouter()

# Initialize Flux client
try:
    flux_client = FluxClient() if settings.BFL_API_KEY else None
    if flux_client:
        logger.info("Flux client initialized successfully")
    else:
        logger.warning("Flux client not initialized - BFL_API_KEY not provided")
except Exception as e:
    logger.error(f"Failed to initialize Flux client: {e}")
    flux_client = None


@router.post("/flux/generate", response_model=ImageGenerationResponse)
async def generate_flux_image(request: FluxGenerationRequest):
    """Generate an image using Flux models (FLUX.1 [pro], FLUX.1 [pro] Ultra)"""
    
    if not flux_client:
        raise HTTPException(
            status_code=503,
            detail="Flux service is currently unavailable. Please check your BFL API key configuration."
        )
    
    try:
        # Validate model-specific parameters
        if request.model == "flux-pro-ultra":
            if not request.aspect_ratio:
                request.aspect_ratio = "16:9"  # Default for Ultra
            # Ultra doesn't use width/height, only aspect_ratio
            kwargs = {
                "aspect_ratio": request.aspect_ratio,
                "prompt_upsampling": request.prompt_upsampling,
                "seed": request.seed,
                "safety_tolerance": request.safety_tolerance,
                "output_format": request.output_format,
                "raw": request.raw,
                "image_prompt": request.image_prompt,
                "image_prompt_strength": request.image_prompt_strength,
                "webhook_url": request.webhook_url,
                "webhook_secret": request.webhook_secret
            }
        else:  # flux-pro
            kwargs = {
                "width": request.width,
                "height": request.height,
                "prompt_upsampling": request.prompt_upsampling,
                "seed": request.seed,
                "safety_tolerance": request.safety_tolerance,
                "output_format": request.output_format,
                "webhook_url": request.webhook_url,
                "webhook_secret": request.webhook_secret
            }
        
        # Generate image synchronously
        result = flux_client.generate_and_wait(
            prompt=request.prompt,
            model=request.model,
            **kwargs
        )
        
        # Process result
        if result.get("status") != "Ready":
            raise HTTPException(
                status_code=500,
                detail=f"Flux generation failed: {result.get('status', 'Unknown error')}"
            )
        
        # Get image URL from result
        image_url = result.get("result", {}).get("sample")
        if not image_url:
            raise HTTPException(
                status_code=500,
                detail="No image URL in Flux response"
            )
        
        # Download and convert to base64
        image_data = flux_client.download_image(image_url)
        image_b64 = base64.b64encode(image_data).decode('utf-8')
        
        # Format response to match existing API structure
        response_data = {
            "created": result.get("created_at", 0),
            "data": [{
                "b64_json": image_b64,
                "url": image_url,
                "revised_prompt": request.prompt  # Flux doesn't revise prompts
            }]
        }
        
        # Add usage info if available
        if "usage" in result:
            response_data["usage"] = result["usage"]
        
        return ImageGenerationResponse(**response_data)
        
    except Exception as e:
        logger.error(f"Error generating Flux image: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Flux generation failed: {str(e)}")


@router.post("/flux/edit", response_model=ImageGenerationResponse)
async def edit_flux_image(request: FluxEditRequest):
    """Edit an image using FLUX.1 Kontext model"""
    
    if not flux_client:
        raise HTTPException(
            status_code=503,
            detail="Flux service is currently unavailable. Please check your BFL API key configuration."
        )
    
    try:
        # Validate Kontext-specific requirements
        if request.model != "flux-kontext":
            raise HTTPException(
                status_code=400,
                detail="Image editing requires flux-kontext model"
            )
        
        if not request.image_prompt:
            raise HTTPException(
                status_code=400,
                detail="image_prompt is required for Flux Kontext editing"
            )
        
        # Prepare parameters for Kontext
        kwargs = {
            "width": request.width,
            "height": request.height,
            "prompt_upsampling": request.prompt_upsampling,
            "seed": request.seed,
            "safety_tolerance": request.safety_tolerance,
            "output_format": request.output_format,
            "image_prompt": request.image_prompt,
            "image_prompt_strength": request.image_prompt_strength,
            "webhook_url": request.webhook_url,
            "webhook_secret": request.webhook_secret
        }
        
        # Generate edited image
        result = flux_client.generate_and_wait(
            prompt=request.prompt,
            model=request.model,
            **kwargs
        )
        
        # Process result
        if result.get("status") != "Ready":
            raise HTTPException(
                status_code=500,
                detail=f"Flux editing failed: {result.get('status', 'Unknown error')}"
            )
        
        # Get image URL from result
        image_url = result.get("result", {}).get("sample")
        if not image_url:
            raise HTTPException(
                status_code=500,
                detail="No image URL in Flux response"
            )
        
        # Download and convert to base64
        image_data = flux_client.download_image(image_url)
        image_b64 = base64.b64encode(image_data).decode('utf-8')
        
        # Format response
        response_data = {
            "created": result.get("created_at", 0),
            "data": [{
                "b64_json": image_b64,
                "url": image_url,
                "revised_prompt": request.prompt
            }]
        }
        
        if "usage" in result:
            response_data["usage"] = result["usage"]
        
        return ImageGenerationResponse(**response_data)
        
    except Exception as e:
        logger.error(f"Error editing Flux image: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Flux editing failed: {str(e)}")


@router.get("/flux/task/{task_id}")
async def get_flux_task_status(task_id: str):
    """Get the status of a Flux generation task"""
    
    if not flux_client:
        raise HTTPException(
            status_code=503,
            detail="Flux service is currently unavailable."
        )
    
    try:
        status = flux_client.get_task_status(task_id)
        return status
    except Exception as e:
        logger.error(f"Error getting Flux task status: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get task status: {str(e)}")


@router.post("/flux/generate/async", response_model=Dict[str, Any])
async def generate_flux_image_async(request: FluxGenerationRequest):
    """Start Flux image generation asynchronously and return task ID"""
    
    if not flux_client:
        raise HTTPException(
            status_code=503,
            detail="Flux service is currently unavailable. Please check your BFL API key configuration."
        )
    
    try:
        # Prepare parameters based on model
        if request.model == "flux-pro-ultra":
            if not request.aspect_ratio:
                request.aspect_ratio = "16:9"
            kwargs = {
                "aspect_ratio": request.aspect_ratio,
                "prompt_upsampling": request.prompt_upsampling,
                "seed": request.seed,
                "safety_tolerance": request.safety_tolerance,
                "output_format": request.output_format,
                "raw": request.raw,
                "image_prompt": request.image_prompt,
                "image_prompt_strength": request.image_prompt_strength,
                "webhook_url": request.webhook_url,
                "webhook_secret": request.webhook_secret
            }
        else:
            kwargs = {
                "width": request.width,
                "height": request.height,
                "prompt_upsampling": request.prompt_upsampling,
                "seed": request.seed,
                "safety_tolerance": request.safety_tolerance,
                "output_format": request.output_format,
                "webhook_url": request.webhook_url,
                "webhook_secret": request.webhook_secret
            }
        
        # Start generation (async)
        result = flux_client.generate_image(
            prompt=request.prompt,
            model=request.model,
            **kwargs
        )
        
        return {
            "task_id": result.get("id"),
            "status": "started",
            "message": "Generation started successfully"
        }
        
    except Exception as e:
        logger.error(f"Error starting Flux generation: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to start generation: {str(e)}")