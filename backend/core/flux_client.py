import os
import logging
import base64
import uuid
import io
import time
import requests
from typing import List, Union, Optional, Dict, Any
from PIL import Image
from backend.core.config import settings

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class FluxClient:
    """
    Client for Flux models (FLUX.1 [pro], FLUX.1 [pro] Ultra, FLUX.1 Kontext) using Black Forest Labs API.
    """

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize the Flux client with BFL API key

        Args:
            api_key: The BFL API key to use (optional, will use from settings if not provided)
        """
        self.api_key = api_key or settings.BFL_API_KEY
        if not self.api_key:
            raise ValueError("BFL API key must be provided")
        
        self.base_url = "https://api.bfl.ml"
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        logger.info("Initialized Flux client with BFL API")

    def generate_image(self, prompt: str, model: str = "flux-pro", **kwargs) -> dict:
        """
        Generate images using Flux models

        Args:
            prompt: Text description of the desired image
            model: The Flux model to use ('flux-pro', 'flux-pro-ultra', 'flux-kontext')
            **kwargs: Additional model-specific parameters

        Returns:
            dict: Response from BFL API with task ID and other metadata
        """
        try:
            # Map model names to BFL API endpoints
            model_endpoints = {
                "flux-pro": "flux-pro",
                "flux-pro-ultra": "flux-pro-ultra", 
                "flux-kontext": "flux-kontext"
            }
            
            if model not in model_endpoints:
                raise ValueError(f"Unsupported model: {model}. Supported models: {list(model_endpoints.keys())}")

            endpoint = f"{self.base_url}/v1/{model_endpoints[model]}"
            
            # Prepare request payload
            payload = {
                "prompt": prompt
            }
            
            # Add model-specific parameters
            if model == "flux-pro":
                # FLUX.1 [pro] parameters
                payload.update({
                    "width": kwargs.get("width", 1024),
                    "height": kwargs.get("height", 1024),
                    "prompt_upsampling": kwargs.get("prompt_upsampling", False),
                    "seed": kwargs.get("seed"),
                    "safety_tolerance": kwargs.get("safety_tolerance", 2),
                    "output_format": kwargs.get("output_format", "jpeg")
                })
                
            elif model == "flux-pro-ultra":
                # FLUX.1 [pro] Ultra parameters
                payload.update({
                    "aspect_ratio": kwargs.get("aspect_ratio", "16:9"),
                    "prompt_upsampling": kwargs.get("prompt_upsampling", False),
                    "seed": kwargs.get("seed"),
                    "safety_tolerance": kwargs.get("safety_tolerance", 2),
                    "output_format": kwargs.get("output_format", "jpeg"),
                    "raw": kwargs.get("raw", False),
                    "image_prompt": kwargs.get("image_prompt"),
                    "image_prompt_strength": kwargs.get("image_prompt_strength", 0.1)
                })
                
            elif model == "flux-kontext":
                # FLUX.1 Kontext parameters (for image editing)
                payload.update({
                    "width": kwargs.get("width", 1024),
                    "height": kwargs.get("height", 1024),
                    "prompt_upsampling": kwargs.get("prompt_upsampling", False),
                    "seed": kwargs.get("seed"),
                    "safety_tolerance": kwargs.get("safety_tolerance", 2),
                    "output_format": kwargs.get("output_format", "jpeg"),
                    "image_prompt": kwargs.get("image_prompt"),  # Required for Kontext
                    "image_prompt_strength": kwargs.get("image_prompt_strength", 0.1)
                })

            # Add webhook parameters if provided
            if kwargs.get("webhook_url"):
                payload["webhook_url"] = kwargs["webhook_url"]
            if kwargs.get("webhook_secret"):
                payload["webhook_secret"] = kwargs["webhook_secret"]

            # Remove None values
            payload = {k: v for k, v in payload.items() if v is not None}

            logger.info(f"Generating image with Flux {model}, prompt length: {len(prompt)}")
            
            # Make API request
            response = requests.post(endpoint, json=payload, headers=self.headers)
            response.raise_for_status()
            
            result = response.json()
            logger.info(f"Flux {model} generation initiated with task ID: {result.get('id')}")
            
            return result

        except requests.exceptions.RequestException as e:
            logger.error(f"Error calling Flux API: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Error generating image with Flux: {str(e)}")
            raise

    def get_task_status(self, task_id: str) -> dict:
        """
        Get the status of a Flux generation task

        Args:
            task_id: The task ID returned from generate_image

        Returns:
            dict: Task status and result if completed
        """
        try:
            endpoint = f"{self.base_url}/v1/get_result"
            params = {"id": task_id}
            
            response = requests.get(endpoint, params=params, headers=self.headers)
            response.raise_for_status()
            
            return response.json()
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Error getting task status: {str(e)}")
            raise

    def wait_for_completion(self, task_id: str, max_wait_time: int = 300, poll_interval: int = 5) -> dict:
        """
        Wait for a Flux generation task to complete

        Args:
            task_id: The task ID to wait for
            max_wait_time: Maximum time to wait in seconds
            poll_interval: How often to check status in seconds

        Returns:
            dict: Final task result
        """
        start_time = time.time()
        
        while time.time() - start_time < max_wait_time:
            status = self.get_task_status(task_id)
            
            if status.get("status") == "Ready":
                logger.info(f"Flux task {task_id} completed successfully")
                return status
            elif status.get("status") == "Error":
                error_msg = status.get("error", "Unknown error")
                logger.error(f"Flux task {task_id} failed: {error_msg}")
                raise Exception(f"Flux generation failed: {error_msg}")
            
            logger.info(f"Flux task {task_id} status: {status.get('status')}, waiting...")
            time.sleep(poll_interval)
        
        raise TimeoutError(f"Flux task {task_id} did not complete within {max_wait_time} seconds")

    def generate_and_wait(self, prompt: str, model: str = "flux-pro", **kwargs) -> dict:
        """
        Generate image and wait for completion (synchronous)

        Args:
            prompt: Text description of the desired image
            model: The Flux model to use
            **kwargs: Additional model-specific parameters

        Returns:
            dict: Final result with image URL/data
        """
        # Start generation
        result = self.generate_image(prompt, model, **kwargs)
        task_id = result.get("id")
        
        if not task_id:
            raise Exception("No task ID returned from Flux API")
        
        # Wait for completion
        return self.wait_for_completion(task_id, kwargs.get("max_wait_time", 300))

    def download_image(self, image_url: str) -> bytes:
        """
        Download image from Flux result URL

        Args:
            image_url: URL of the generated image

        Returns:
            bytes: Image data
        """
        try:
            response = requests.get(image_url)
            response.raise_for_status()
            return response.content
        except requests.exceptions.RequestException as e:
            logger.error(f"Error downloading image: {str(e)}")
            raise