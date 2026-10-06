import logging
from openai import AzureOpenAI, OpenAI
from .config import settings
from .sora import Sora
from .gpt_image import GPTImageClient
from .flux_client import FluxClient
import json
from datetime import datetime, timedelta, timezone

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Sora client
try:
    sora_client = Sora(
        resource_name=settings.SORA_AOAI_RESOURCE,
        deployment_name=settings.SORA_DEPLOYMENT,
        api_key=settings.SORA_AOAI_API_KEY
    )
    logger.info(
        f"Initialized Sora client with resource: {settings.SORA_AOAI_RESOURCE}")
except Exception as e:
    logger.error(f"Failed to initialize Sora client: {str(e)}")
    sora_client = None

# Initialize GPT-Image-1 client
try:
    # Using OpenAI API directly for GPT-Image-1
    dalle_client = GPTImageClient(
        api_key=settings.OPENAI_API_KEY,
        organization_id=settings.OPENAI_ORG_ID if settings.OPENAI_ORG_ID else None
    )
    logger.info("Initialized GPT-Image-1 client using OpenAI API.")
except Exception as e:
    logger.error(f"Failed to initialize GPT-Image-1 client: {str(e)}")
    dalle_client = None

# Initialize Flux client
try:
    flux_client = None
    # Determine whether we have credentials for the configured provider
    if settings.FLUX_MODEL_PROVIDER == "foundry":
        if settings.FOUNDRY_API_KEY and settings.FOUNDRY_ENDPOINT:
            flux_client = FluxClient()
        else:
            logger.warning("Flux client not initialized - Foundry API configuration missing")
    else:
        if settings.BFL_API_KEY:
            flux_client = FluxClient()
        else:
            logger.warning("Flux client not initialized - BFL_API_KEY not provided")

    if flux_client:
        logger.info(f"Initialized Flux client with {flux_client.provider} provider")
except Exception as e:
    logger.error(f"Failed to initialize Flux client: {str(e)}")
    flux_client = None

# Initialize LLM client
try:
    llm_client = AzureOpenAI(
        azure_endpoint=f"https://{settings.LLM_AOAI_RESOURCE}.openai.azure.com/",
        api_key=settings.LLM_AOAI_API_KEY,
        # TODO: make configurable. Video generation uses 2025-02-15-preview (does not work with LLM)
        api_version="2025-01-01-preview"
    )
    logger.info(
        f"Initialized LLM client with resource: {settings.LLM_AOAI_RESOURCE}")
except Exception as e:
    logger.error(f"Failed to initialize LLM client: {str(e)}")
    llm_client = None
