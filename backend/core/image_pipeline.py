import base64
import io
import logging
import os
import re
import tempfile
import uuid
from datetime import datetime
from typing import Dict, List, Optional, Tuple

import requests
from fastapi import HTTPException, UploadFile
from PIL import Image

from backend.core import dalle_client, llm_client, flux_client
from backend.core.analyze import ImageAnalyzer
from backend.core.config import settings
from backend.core.dataverse_service import DataverseService, DataverseError
from backend.core.instructions import analyze_image_system_message
from backend.models.images import (
    ImageEditRequest,
    ImageGenerationRequest,
    ImageGenerationResponse,
    ImagePipelineRequest,
    ImagePipelineResponse,
    ImageSaveRequest,
    ImageSaveResponse,
    PipelineAction,
    PipelineStepResult,
    TokenUsage,
    InputTokensDetails,
)

logger = logging.getLogger(__name__)


class ImagePipelineService:
    """Service that centralises the image generation/edit/save pipeline logic."""

    def __init__(self) -> None:
        self._image_analyzer: Optional[ImageAnalyzer] = None

    # ------------------------------------------------------------------
    # Generation / Edit helpers
    # ------------------------------------------------------------------
    async def generate(self, request: ImageGenerationRequest) -> ImageGenerationResponse:
        """Generate images via the configured image generation client."""
        try:
            # Route to appropriate client based on model
            if request.model.startswith("flux-"):
                return await self._generate_flux(request)
            else:
                return await self._generate_gpt_image(request)
        except Exception as exc:  # pragma: no cover - delegated to HTTP response
            logger.error("Error generating image: %s", exc, exc_info=True)
            raise HTTPException(status_code=500, detail=str(exc))

    async def _generate_gpt_image(self, request: ImageGenerationRequest) -> ImageGenerationResponse:
        """Generate images via GPT-Image-1 client."""
        params: Dict[str, object] = {
            "prompt": request.prompt,
            "model": request.model,
            "n": request.n,
            "size": request.size,
        }

        if request.model == "gpt-image-1":
            if request.quality:
                params["quality"] = request.quality
            params["background"] = request.background
            if request.output_format != "png":
                params["output_format"] = request.output_format
            if (
                request.output_format in ["webp", "jpeg"]
                and request.output_compression != 100
            ):
                params["output_compression"] = request.output_compression
            if request.moderation != "auto":
                params["moderation"] = request.moderation
            if request.user:
                params["user"] = request.user

        response = dalle_client.generate_image(**params)
        token_usage = self._extract_token_usage(response)

        return ImageGenerationResponse(
            success=True,
            message="Refer to the imgen_model_response for details",
            imgen_model_response=response,
            token_usage=token_usage,
        )

    async def _generate_flux(self, request: ImageGenerationRequest) -> ImageGenerationResponse:
        """Generate images via Flux client."""
        if not flux_client:
            raise HTTPException(
                status_code=503,
                detail="Flux service is currently unavailable. Please check your BFL API key configuration."
            )

        provider = getattr(flux_client, "provider", None)

        # Prepare Flux-specific parameters
        kwargs = {}
        if request.model == "flux-pro-ultra":
            if request.aspect_ratio:
                kwargs["aspect_ratio"] = request.aspect_ratio
            else:
                kwargs["aspect_ratio"] = "16:9"  # Default
            kwargs.update({
                "raw": request.raw,
                "image_prompt": request.image_prompt,
                "image_prompt_strength": request.image_prompt_strength,
            })
        else:  # flux-pro or flux-kontext
            kwargs.update({
                "width": request.width or 1024,
                "height": request.height or 1024,
            })
            if request.model == "flux-kontext":
                kwargs.update({
                    "image_prompt": request.image_prompt,
                    "image_prompt_strength": request.image_prompt_strength,
                })

        # Common Flux parameters
        kwargs.update({
            "prompt_upsampling": request.prompt_upsampling,
            "seed": request.seed,
            "safety_tolerance": request.safety_tolerance,
            "output_format": request.output_format or "jpeg",
            "webhook_url": request.webhook_url,
            "webhook_secret": request.webhook_secret,
            "n": request.n,
        })

        # Generate image and wait for completion
        result = flux_client.generate_and_wait(
            prompt=request.prompt,
            model=request.model,
            **kwargs
        )

        # Process result based on provider
        if provider == "foundry":
            data_entries = result.get("data") or result.get("output") or result.get("outputs")
            if not data_entries:
                raise HTTPException(status_code=500, detail="Flux response did not contain image data")

            formatted_data = []
            for entry in data_entries:
                entry_copy = dict(entry)
                b64_data = entry_copy.get("b64_json")
                image_url = entry_copy.get("url")

                if not b64_data and image_url:
                    try:
                        image_bytes = flux_client.download_image(image_url)
                    except Exception as exc:  # pragma: no cover - HTTPException raised after
                        logger.error("Failed to download Flux image: %s", exc)
                        raise HTTPException(status_code=500, detail="Failed to download image from Flux response") from exc
                    b64_data = base64.b64encode(image_bytes).decode("utf-8")
                    entry_copy["b64_json"] = b64_data

                if not b64_data:
                    raise HTTPException(status_code=500, detail="Flux response missing image data")

                entry_copy.setdefault("revised_prompt", request.prompt)
                formatted_data.append(entry_copy)

            flux_response = {
                "created": result.get("created") or int(datetime.utcnow().timestamp()),
                "data": formatted_data,
            }
        else:
            # Process async provider (e.g., BFL)
            if result.get("status") != "Ready":
                raise HTTPException(
                    status_code=500,
                    detail=f"Flux generation failed: {result.get('status', 'Unknown error')}"
                )

            image_url = result.get("result", {}).get("sample")
            if not image_url:
                raise HTTPException(status_code=500, detail="No image URL in Flux response")

            image_data = flux_client.download_image(image_url)
            image_b64 = base64.b64encode(image_data).decode('utf-8')

            flux_response = {
                "created": result.get("created_at", 0),
                "data": [{
                    "b64_json": image_b64,
                    "url": image_url,
                    "revised_prompt": request.prompt
                }]
            }

        return ImageGenerationResponse(
            success=True,
            message="Image generated successfully with Flux",
            imgen_model_response=flux_response,
            token_usage=None,  # Flux doesn't provide token usage
        )

    async def edit(self, request: ImageEditRequest) -> ImageGenerationResponse:
        """Edit images via the configured client using JSON payload data."""
        try:
            params: Dict[str, object] = {
                "prompt": request.prompt,
                "model": request.model,
                "n": request.n,
                "size": request.size,
                "image": request.image,
            }

            if request.mask:
                params["mask"] = request.mask

            if request.model == "gpt-image-1":
                if request.quality:
                    params["quality"] = request.quality
                if request.output_format != "png":
                    params["output_format"] = request.output_format
                if (
                    request.output_format in ["webp", "jpeg"]
                    and request.output_compression != 100
                ):
                    params["output_compression"] = request.output_compression
                if request.input_fidelity and request.input_fidelity != "low":
                    params["input_fidelity"] = request.input_fidelity
                if request.user:
                    params["user"] = request.user

                if isinstance(request.image, list):
                    image_count = len(request.image)
                    if image_count > 1 and not settings.OPENAI_ORG_VERIFIED:
                        logger.warning(
                            "Using multiple reference images requires organization verification"
                        )

            response = dalle_client.edit_image(**params)
            token_usage = self._extract_token_usage(response)

            return ImageGenerationResponse(
                success=True,
                message="Refer to the imgen_model_response for details",
                imgen_model_response=response,
                token_usage=token_usage,
            )
        except Exception as exc:  # pragma: no cover - delegated to HTTP response
            logger.error("Error editing image: %s", exc, exc_info=True)
            raise HTTPException(status_code=500, detail=str(exc))

    async def edit_with_uploads(
        self,
        *,
        prompt: str,
        model: str,
        n: int,
        size: str,
        quality: str,
        output_format: str,
        input_fidelity: str,
        images: List[UploadFile],
        mask: Optional[UploadFile] = None,
    ) -> ImageGenerationResponse:
        """Edit images using uploaded multipart files."""

        if input_fidelity not in ["low", "high"]:
            raise HTTPException(
                status_code=400,
                detail="input_fidelity must be either 'low' or 'high'",
            )

        max_file_size_mb = settings.GPT_IMAGE_MAX_FILE_SIZE_MB
        temp_files: List[Tuple[int, str]] = []

        try:
            image_file_paths: List[str] = []
            for idx, upload in enumerate(images):
                contents = await upload.read()
                file_size_mb = len(contents) / (1024 * 1024)
                if file_size_mb > max_file_size_mb:
                    raise HTTPException(
                        status_code=400,
                        detail=(
                            f"Image {idx + 1} exceeds maximum size of {max_file_size_mb}MB"
                        ),
                    )

                ext = self._determine_extension(upload.content_type, contents)
                temp_fd, temp_path = tempfile.mkstemp(suffix=f".{ext}")
                temp_files.append((temp_fd, temp_path))

                with os.fdopen(temp_fd, "wb") as file_obj:
                    file_obj.write(contents)

                image_file_paths.append(temp_path)
                logger.info(
                    "Saved image %s to %s with format %s", idx + 1, temp_path, ext
                )

            mask_path: Optional[str] = None
            if mask:
                mask_contents = await mask.read()
                mask_ext = self._determine_extension(mask.content_type, mask_contents)
                mask_fd, mask_path = tempfile.mkstemp(suffix=f".{mask_ext}")
                temp_files.append((mask_fd, mask_path))
                with os.fdopen(mask_fd, "wb") as mask_file:
                    mask_file.write(mask_contents)
                logger.info("Saved mask to %s with format %s", mask_path, mask_ext)

            params: Dict[str, object] = {
                "prompt": prompt,
                "model": model,
                "n": n,
                "size": size,
            }

            if model == "gpt-image-1":
                params["quality"] = quality
                if input_fidelity != "low":
                    params["input_fidelity"] = input_fidelity

            response = await self._invoke_edit_with_files(
                image_file_paths, mask_path, params
            )
            token_usage = self._extract_token_usage(response)

            return ImageGenerationResponse(
                success=True,
                message="Refer to the imgen_model_response for details",
                imgen_model_response=response,
                token_usage=token_usage,
            )
        except HTTPException:
            raise
        except Exception as exc:  # pragma: no cover - delegated to HTTP response
            logger.error("Error editing image upload: %s", exc, exc_info=True)
            raise HTTPException(status_code=500, detail=str(exc))
        finally:
            self._cleanup_temp_files(temp_files)

    async def save(
        self,
        request: ImageSaveRequest,
        *,
        dataverse_service: DataverseService,
    ) -> ImageSaveResponse:
        """Persist generated images directly to Dataverse using file attachments."""

        if (
            not request.generation_response
            or not request.generation_response.imgen_model_response
        ):
            raise HTTPException(
                status_code=400,
                detail="No valid image generation response provided",
            )

        images_data = request.generation_response.imgen_model_response.get(
            "data", []
        )
        if not images_data:
            raise HTTPException(
                status_code=400,
                detail="No images found in the generation response",
            )

        if not request.save_all:
            images_data = [images_data[0]]

        combined_metadata = self._build_base_metadata(request)
        saved_images: List[Dict[str, object]] = []

        for idx, img_data in enumerate(images_data):
            img_file, filename, has_transparency = self._prepare_image_file(
                img_data, request.prompt, idx
            )
            try:
                image_metadata = combined_metadata.copy()
                image_metadata["image_index"] = str(idx + 1)
                image_metadata["total_images"] = str(len(images_data))

                img_file.seek(0)
                image_bytes = img_file.read()

                metadata_dict = {
                    "media_type": "image",
                    "blob_name": filename,
                    "container": "dataverse",
                    "filename": filename,
                    "content_type": self._determine_content_type(img_data),
                    "folder_path": request.folder_path,
                    "prompt": request.prompt,
                    "model": request.model,
                    "has_transparency": has_transparency,
                    "created_at": datetime.utcnow().isoformat(),
                }

                # Add image dimensions if available
                try:
                    with Image.open(io.BytesIO(image_bytes)) as pil_img:
                        metadata_dict["width"] = pil_img.width
                        metadata_dict["height"] = pil_img.height
                        metadata_dict["size"] = len(image_bytes)
                except Exception as e:
                    logger.warning(f"Failed to get image properties: {e}")
                    metadata_dict.setdefault("size", len(image_bytes))
                else:
                    metadata_dict.setdefault("size", len(image_bytes))

                # Add generation-specific metadata
                quality = getattr(request, "quality", None)
                if quality and quality != "auto":
                    metadata_dict["quality"] = quality

                background = getattr(request, "background", None)
                if background and background != "auto":
                    metadata_dict["background"] = background

                output_format = getattr(request, "output_format", None)
                if output_format:
                    metadata_dict["output_format"] = output_format

                # Add custom metadata
                if image_metadata:
                    custom_meta = {
                        key: value
                        for key, value in image_metadata.items()
                        if value is not None
                    }
                    if custom_meta:
                        metadata_dict["custom_metadata"] = custom_meta

                try:
                    dataverse_record = dataverse_service.create_asset_metadata(metadata_dict)
                except DataverseError as exc:
                    logger.error("Failed to create Dataverse metadata: %s", exc)
                    raise HTTPException(status_code=503, detail="Dataverse service error")

                asset_id = dataverse_record.get("id")
                if not asset_id:
                    raise HTTPException(status_code=500, detail="Dataverse did not return an asset identifier")

                container_value = "dataverse"
                blob_reference = filename
                asset_url = f"/api/v1/gallery/assets/{asset_id}/content"

                try:
                    dataverse_service.upload_asset_file(
                        asset_id,
                        image_bytes,
                        filename=filename,
                        content_type=metadata_dict.get("content_type"),
                    )
                    try:
                        dataverse_service.update_asset_metadata(asset_id, {"url": f"dataverse://{asset_id}"})
                    except DataverseError as update_exc:
                        logger.debug("Unable to update asset URL metadata for %s: %s", asset_id, update_exc)
                except DataverseError as exc:
                    logger.warning("Dataverse file upload failed for asset %s: %s", asset_id, exc)
                    image_dir = os.path.abspath(settings.IMAGE_DIR)
                    os.makedirs(image_dir, exist_ok=True)

                    _, ext = os.path.splitext(filename or "")
                    ext = ext or ".png"
                    local_filename = f"{asset_id}{ext}"
                    local_path = os.path.join(image_dir, local_filename)

                    try:
                        with open(local_path, "wb") as out_file:
                            out_file.write(image_bytes)
                    except Exception as write_exc:
                        logger.error("Failed to write fallback file %s: %s", local_path, write_exc)
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
                        logger.debug("Unable to update fallback metadata for %s: %s", asset_id, update_exc)

                    container_value = "local"
                    blob_reference = local_filename
                    asset_url = f"/{settings.IMAGE_DIR.rstrip('/')}/{local_filename}"

                result = {
                    "success": True,
                    "asset_id": asset_id,
                    "blob_name": blob_reference,
                    "container": container_value,
                    "url": asset_url,
                    "original_filename": filename,
                    "content_type": metadata_dict.get("content_type"),
                    "size": metadata_dict.get("size"),
                    "width": metadata_dict.get("width"),
                    "height": metadata_dict.get("height"),
                    "folder_path": request.folder_path,
                }

                saved_images.append(result)
            finally:
                img_file.close()

        analysis_results: List[Dict[str, object]] = []
        analyzed = False

        if (
            request.analyze
            and saved_images
            and dataverse_service
        ):
            analyzed = True
            analysis_results = self._run_analysis_on_saved_images(
                saved_images,
                dataverse_service,
                request,
            )

        return ImageSaveResponse(
            success=True,
            message=f"Saved {len(saved_images)} image(s)",
            saved_images=saved_images,
            total_saved=len(saved_images),
            prompt=request.prompt,
            analysis_results=analysis_results if analysis_results else None,
            analyzed=analyzed,
        )

    async def process_pipeline(
        self,
        pipeline_request: ImagePipelineRequest,
        *,
        dataverse_service: DataverseService,
        source_images: Optional[List[UploadFile]] = None,
        mask: Optional[UploadFile] = None,
    ) -> ImagePipelineResponse:
        """Execute the requested pipeline flow end-to-end."""

        steps: List[PipelineStepResult] = []
        generation_response: Optional[ImageGenerationResponse] = None
        save_response: Optional[ImageSaveResponse] = None

        action_step = (
            "edit"
            if pipeline_request.action == PipelineAction.EDIT or source_images
            else "generate"
        )

        try:
            if action_step == "edit":
                if source_images:
                    generation_response = await self.edit_with_uploads(
                        prompt=pipeline_request.prompt,
                        model=pipeline_request.model,
                        n=pipeline_request.n,
                        size=pipeline_request.size,
                        quality=pipeline_request.quality or "auto",
                        output_format=pipeline_request.output_format or "png",
                        input_fidelity=pipeline_request.input_fidelity or "low",
                        images=source_images,
                        mask=mask,
                    )
                else:
                    edit_request = ImageEditRequest(
                        prompt=pipeline_request.prompt,
                        model=pipeline_request.model,
                        n=pipeline_request.n,
                        size=pipeline_request.size,
                        response_format=pipeline_request.response_format,
                        quality=pipeline_request.quality,
                        output_format=pipeline_request.output_format,
                        output_compression=pipeline_request.output_compression,
                        background=pipeline_request.background,
                        moderation=pipeline_request.moderation,
                        user=pipeline_request.user,
                        input_fidelity=pipeline_request.input_fidelity,
                        image=self._resolve_edit_images(pipeline_request),
                        mask=pipeline_request.mask_image_url,
                    )
                    generation_response = await self.edit(edit_request)
                steps.append(
                    PipelineStepResult(
                        step="edit",
                        success=True,
                        message="Image edit completed",
                    )
                )
            else:
                # Parse width and height from size for Flux models
                width = None
                height = None
                if pipeline_request.model.startswith("flux-") and pipeline_request.size and pipeline_request.size != "auto":
                    try:
                        width_str, height_str = pipeline_request.size.split("x")
                        width = int(width_str)
                        height = int(height_str)
                    except (ValueError, AttributeError):
                        # If parsing fails, leave as None and let the model use defaults
                        pass
                
                generation_request = ImageGenerationRequest(
                    prompt=pipeline_request.prompt,
                    model=pipeline_request.model,
                    n=pipeline_request.n,
                    size=pipeline_request.size,
                    response_format=pipeline_request.response_format,
                    quality=pipeline_request.quality,
                    output_format=pipeline_request.output_format,
                    output_compression=pipeline_request.output_compression,
                    background=pipeline_request.background,
                    moderation=pipeline_request.moderation,
                    user=pipeline_request.user,
                    width=width,
                    height=height,
                )
                generation_response = await self.generate(generation_request)
                steps.append(
                    PipelineStepResult(
                        step="generate",
                        success=True,
                        message="Image generation completed",
                    )
                )
        except HTTPException as exc:
            steps.append(
                PipelineStepResult(
                    step=action_step,
                    success=False,
                    message=str(exc.detail),
                )
            )
            raise
        except Exception as exc:  # pragma: no cover - delegated to HTTP response
            steps.append(
                PipelineStepResult(
                    step=action_step,
                    success=False,
                    message=str(exc),
                )
            )
            raise HTTPException(status_code=500, detail=str(exc))

        if (
            pipeline_request.save_options.enabled
            and generation_response
            and dataverse_service
        ):
            save_request = ImageSaveRequest(
                generation_response=generation_response,
                prompt=pipeline_request.prompt,
                model=pipeline_request.model,
                size=pipeline_request.size,
                background=(
                    pipeline_request.save_options.background
                    or pipeline_request.background
                ),
                output_format=(
                    pipeline_request.save_options.output_format
                    or pipeline_request.output_format
                    or "png"
                ),
                save_all=pipeline_request.save_options.save_all,
                folder_path=pipeline_request.save_options.folder_path,
                analyze=pipeline_request.analysis_options.enabled,
                metadata=self._merge_pipeline_metadata(pipeline_request),
            )
            try:
                save_response = await self.save(
                    save_request,
                    dataverse_service=dataverse_service,
                )
                steps.append(
                    PipelineStepResult(
                        step="save",
                        success=True,
                        message=f"Saved {save_response.total_saved} image(s)",
                    )
                )
            except HTTPException as exc:
                steps.append(
                    PipelineStepResult(
                        step="save",
                        success=False,
                        message=str(exc.detail),
                    )
                )
                raise

        elif pipeline_request.analysis_options.enabled:
            steps.append(
                PipelineStepResult(
                    step="analyze",
                    success=False,
                    message="Analysis requires saved images; enable save_options",
                )
            )

        overall_success = all(step.success for step in steps)
        message = "Pipeline completed"
        if not overall_success:
            message = "Pipeline completed with issues"

        return ImagePipelineResponse(
            success=overall_success,
            message=message,
            steps=steps,
            generation=generation_response,
            save=save_response,
        )

    # ------------------------------------------------------------------
    # Internal utilities
    # ------------------------------------------------------------------
    @staticmethod
    def _extract_token_usage(response: Dict[str, object]) -> Optional[TokenUsage]:
        if "usage" not in response:
            return None

        usage = response["usage"]
        input_tokens_details = None
        if isinstance(usage, dict) and "input_tokens_details" in usage:
            details = usage.get("input_tokens_details", {})
            input_tokens_details = InputTokensDetails(
                text_tokens=details.get("text_tokens", 0),
                image_tokens=details.get("image_tokens", 0),
            )

        return TokenUsage(
            total_tokens=usage.get("total_tokens", 0),
            input_tokens=usage.get("input_tokens", 0),
            output_tokens=usage.get("output_tokens", 0),
            input_tokens_details=input_tokens_details,
        )

    @staticmethod
    def _determine_extension(content_type: Optional[str], contents: bytes) -> str:
        ext = (content_type or "image/png").split("/")[-1]
        if ext not in {"jpeg", "jpg", "png", "webp"}:
            try:
                with Image.open(io.BytesIO(contents)) as pil_img:
                    ext = pil_img.format.lower() if pil_img.format else "png"
            except Exception:
                ext = "png"
        if ext == "jpg":
            ext = "jpeg"
        return ext

    async def _invoke_edit_with_files(
        self,
        image_paths: List[str],
        mask_path: Optional[str],
        params: Dict[str, object],
    ) -> Dict[str, object]:
        if len(image_paths) == 1:
            with open(image_paths[0], "rb") as image_file:
                params["image"] = image_file
                if mask_path:
                    with open(mask_path, "rb") as mask_file:
                        params["mask"] = mask_file
                        return dalle_client.edit_image(**params)
                return dalle_client.edit_image(**params)

        open_files: List[io.BufferedReader] = []
        try:
            image_files = []
            for path in image_paths:
                file_obj = open(path, "rb")
                open_files.append(file_obj)
                image_files.append(file_obj)
            params["image"] = image_files

            if mask_path:
                mask_file = open(mask_path, "rb")
                open_files.append(mask_file)
                params["mask"] = mask_file

            return dalle_client.edit_image(**params)
        finally:
            for file_obj in open_files:
                file_obj.close()

    @staticmethod
    def _cleanup_temp_files(temp_files: List[Tuple[int, str]]) -> None:
        for _, path in temp_files:
            try:
                if os.path.exists(path):
                    os.remove(path)
            except Exception as exc:
                logger.warning("Failed to remove temp file %s: %s", path, exc)

    def _prepare_image_file(
        self,
        img_data: Dict[str, object],
        prompt: Optional[str],
        idx: int,
    ) -> Tuple[io.BytesIO, str, Optional[bool]]:
        img_file = io.BytesIO()
        filename = f"generated_image_{idx + 1}.png"
        has_transparency: Optional[bool] = None
        img_format = "PNG"

        if "b64_json" in img_data:
            image_bytes = base64.b64decode(img_data["b64_json"])
            img_file = io.BytesIO(image_bytes)

            with Image.open(img_file) as image:
                img_format = image.format or "PNG"
                has_transparency = image.mode == "RGBA" and "A" in image.getbands()
                if has_transparency and img_format.upper() != "PNG":
                    img_format = "PNG"
                    converted = io.BytesIO()
                    image.save(converted, format="PNG")
                    converted.seek(0)
                    img_file = converted
                img_file.seek(0)

            filename = self._generate_filename(prompt, img_format.lower(), idx)
        elif "url" in img_data:
            response = requests.get(img_data["url"])
            if response.status_code != 200:
                logger.error(
                    "Failed to download image from URL: %s", response.status_code
                )
                raise HTTPException(
                    status_code=500,
                    detail="Failed to download image from URL",
                )
            img_file = io.BytesIO(response.content)
            filename = self._generate_filename(prompt, "png", idx)

        img_file.seek(0)
        return img_file, filename, has_transparency

    @staticmethod
    def _build_base_metadata(request: ImageSaveRequest) -> Dict[str, object]:
        metadata: Dict[str, object] = {}
        if request.prompt:
            metadata["prompt"] = request.prompt
        if request.model:
            metadata["model"] = request.model
        if request.background:
            metadata["background"] = request.background
        if request.size:
            metadata["size"] = request.size
        if request.metadata:
            for key, value in request.metadata.items():
                if value is not None:
                    metadata[str(key)] = value
        return metadata

    def _determine_content_type(self, img_data: Dict[str, object]) -> str:
        """Determine content type from image data"""
        if "b64_json" in img_data:
            # Try to determine from image format
            try:
                image_bytes = base64.b64decode(img_data["b64_json"])
                with Image.open(io.BytesIO(image_bytes)) as img:
                    img_format = img.format.lower() if img.format else "png"
                    format_map = {
                        "jpeg": "image/jpeg",
                        "jpg": "image/jpeg", 
                        "png": "image/png",
                        "webp": "image/webp",
                        "gif": "image/gif"
                    }
                    return format_map.get(img_format, "image/png")
            except Exception:
                pass
        return "image/png"  # Default fallback

    def _run_analysis_on_saved_images(
        self,
        saved_images: List[Dict[str, object]],
        dataverse_service: DataverseService,
        request: ImageSaveRequest,
    ) -> List[Dict[str, object]]:
        logger.info(
            "Starting analysis for %s saved images", len(saved_images)
        )
        analyzer = self._get_analyzer()
        analysis_results: List[Dict[str, object]] = []

        for saved_image in saved_images:
            try:
                asset_id = str(saved_image["asset_id"])
                
                # Get image data from Dataverse
                asset_metadata = dataverse_service.get_asset_metadata(asset_id, "image")
                if not asset_metadata:
                    raise Exception("Asset metadata not found in Dataverse")

                image_base64 = asset_metadata.get("image_data")
                if not image_base64:
                    try:
                        file_bytes, _, _ = dataverse_service.download_asset_file(asset_id)
                        if file_bytes:
                            image_base64 = base64.b64encode(file_bytes).decode("utf-8")
                    except DataverseError as download_exc:
                        raise Exception(f"Unable to retrieve image file: {download_exc}") from download_exc

                if not image_base64:
                    raise Exception("Image content not available for analysis")
                custom_prompt = None
                if request.metadata and request.metadata.get("analysis_prompt"):
                    custom_prompt = str(request.metadata["analysis_prompt"])

                analysis = analyzer.image_chat(
                    image_base64,
                    custom_prompt or analyze_image_system_message,
                )

                analysis_data = {
                    "summary": analysis.get("description", "No summary provided"),
                    "products": analysis.get("products", "None identified"),
                    "tags": analysis.get("tags", []),
                    "feedback": analysis.get("feedback", "No feedback provided"),
                    "analyzed_at": datetime.utcnow().isoformat(),
                }

                dataverse_service.update_asset_metadata(
                    asset_id,
                    {
                        "analysis": analysis_data,
                        "has_analysis": True,
                    },
                    media_type="image",
                )

                analysis_results.append(
                    {
                        "asset_id": asset_id,
                        "analysis": analysis,
                        "success": True,
                    }
                )
            except Exception as exc:
                logger.error(
                    "Failed to analyze image %s: %s", saved_image.get("asset_id"), exc
                )
                analysis_results.append(
                    {
                        "asset_id": saved_image.get("asset_id"),
                        "error": str(exc),
                        "success": False,
                    }
                )

        return analysis_results

    def _generate_filename(
        self,
        prompt: Optional[str],
        extension: str,
        idx: int,
    ) -> str:
        base_prompt = (prompt or "generated_image").strip()
        safe_prompt = re.sub(r"[^a-zA-Z0-9_\-]", "_", base_prompt)
        safe_prompt = re.sub(r"_+", "_", safe_prompt).strip("_.")
        if not safe_prompt:
            safe_prompt = "generated_image"
        safe_prompt = safe_prompt[:50]
        unique_suffix = uuid.uuid4().hex[:8]
        filename = f"{safe_prompt}_{idx + 1}_{unique_suffix}.{extension}"
        return self._normalize_filename(filename)

    @staticmethod
    def _normalize_filename(filename: str) -> str:
        stem, dot, suffix = filename.rpartition(".")
        if not dot:
            stem = filename
            suffix = ""
        stem = re.sub(r"[^a-zA-Z0-9_\-]", "_", stem)
        stem = re.sub(r"_+", "_", stem).strip("_.")
        if not stem:
            stem = "generated_image"
        normalized = f"{stem}.{suffix}" if suffix else stem
        if len(normalized) > 200:
            if suffix:
                normalized = f"{stem[:200 - len(suffix) - 1]}.{suffix}"
            else:
                normalized = stem[:200]
        return normalized

    def _get_analyzer(self) -> ImageAnalyzer:
        if not self._image_analyzer:
            self._image_analyzer = ImageAnalyzer(llm_client, settings.LLM_DEPLOYMENT)
        return self._image_analyzer

    @staticmethod
    def _merge_pipeline_metadata(request: ImagePipelineRequest) -> Dict[str, object]:
        metadata: Dict[str, object] = request.metadata.copy() if request.metadata else {}
        if request.save_options.metadata:
            metadata.update(request.save_options.metadata)
        if request.analysis_options.custom_prompt:
            metadata["analysis_prompt"] = request.analysis_options.custom_prompt
        return metadata

    @staticmethod
    def _resolve_edit_images(request: ImagePipelineRequest) -> List[str]:
        images: List[str] = []
        if request.source_image_urls:
            images.extend([str(url) for url in request.source_image_urls])
        if request.source_image_base64:
            images.extend(request.source_image_base64)
        if not images:
            raise HTTPException(
                status_code=400,
                detail="No source images provided for edit action",
            )
        return images
