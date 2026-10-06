from pydantic_settings import BaseSettings
from typing import List, Optional
from pydantic import Extra, Field, validator
from pathlib import Path


class Settings(BaseSettings):
    # API Settings
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "Vision Design API"

    # Model Provider Configuration
    MODEL_PROVIDER: str = "azure"  # Can be 'azure' or 'openai'

    # Azure OpenAI for Sora Video Generation
    SORA_AOAI_RESOURCE: Optional[str] = None  # The Azure OpenAI resource name for Sora
    SORA_DEPLOYMENT: Optional[str] = None  # The Sora deployment name
    SORA_AOAI_API_KEY: Optional[str] = None  # The Azure OpenAI API key for Sora

    # Azure OpenAI for LLM
    # The Azure OpenAI resource name for LLM
    LLM_AOAI_RESOURCE: Optional[str] = None
    LLM_DEPLOYMENT: Optional[str] = None  # The LLM deployment name
    LLM_AOAI_API_KEY: Optional[str] = None  # The Azure OpenAI API key for LLM

    # Azure OpenAI for Image Generation
    # The Azure OpenAI resource name for image generation
    IMAGEGEN_AOAI_RESOURCE: Optional[str] = None
    # The image generation deployment name
    IMAGEGEN_DEPLOYMENT: Optional[str] = None
    # The Azure OpenAI API key for image generation
    IMAGEGEN_AOAI_API_KEY: Optional[str] = None

    # OpenAI API for Image Generation with GPT-Image-1
    OPENAI_API_KEY: Optional[str] = None
    OPENAI_ORG_ID: Optional[str] = None  # Organization ID for OpenAI
    # Whether organization is verified on OpenAI
    OPENAI_ORG_VERIFIED: bool = False
    GPT_IMAGE_MAX_TOKENS: int = 150000  # Maximum token usage limit

    # Black Forest Labs API for Flux Models
    BFL_API_KEY: Optional[str] = None  # BFL API key for Flux models
    
    # Foundry API for Flux Models (alternative hosting)
    FOUNDRY_API_KEY: Optional[str] = None  # Foundry API key for hosted Flux models
    FOUNDRY_ENDPOINT: Optional[str] = None  # Foundry API endpoint URL
    # Optional, full endpoints for specific Flux deployments (if Foundry uses direct OpenAI-style deployment URLs)
    FOUNDRY_DEPLOYMENT_FLUX_PRO: Optional[str] = None
    FOUNDRY_FLUX_PRO_ENDPOINT: Optional[str] = None
    FOUNDRY_DEPLOYMENT_FLUX_KONTEXT: Optional[str] = None
    FOUNDRY_FLUX_KONTEXT_ENDPOINT: Optional[str] = None
    FLUX_MODEL_PROVIDER: str = "bfl"  # Model provider: 'bfl' or 'foundry'

    # Microsoft Dataverse Settings (Primary metadata and storage)
    DATAVERSE_ENVIRONMENT_URL: Optional[str] = None  # e.g., https://org.crm.dynamics.com/
    DATAVERSE_CLIENT_ID: Optional[str] = None  # Azure AD app client ID
    DATAVERSE_CLIENT_SECRET: Optional[str] = None  # Azure AD app client secret
    AZURE_TENANT_ID: Optional[str] = None  # Optional tenant for client credentials auth
    DATAVERSE_TABLE_VISIONASSETS: str = "dystudio_visionassets"
    DATAVERSE_TABLE_ASSETTAGS: str = "dystudio_assettags"
    DATAVERSE_TABLE_GENERATIONHISTORY: str = "dystudio_generationhistories"
    DATAVERSE_USE_MANAGED_IDENTITY: bool = True
    DATAVERSE_API_VERSION: str = "9.2"
    DATAVERSE_FIELD_PREFIX: str = "dystudio"  # Dataverse custom field prefix
    DATAVERSE_USE_PAC_AUTH: bool = True  # Reuse PAC CLI tokens when available
    DATAVERSE_PAC_PROFILE: Optional[str] = None  # Optional PAC profile hint
    
    # CORS Configuration  
    CORS_ALLOWED_ORIGINS: str = Field(
        default="*",
        description="Comma-separated list of allowed CORS origins, or * for all origins"
    )
    
    # GitHub Integration
    GITHUB_TOKEN: Optional[str] = None  # GitHub personal access token
    GITHUB_REPO_OWNER: Optional[str] = None  # Repository owner for integration
    GITHUB_REPO_NAME: Optional[str] = None  # Repository name for integration

    # Azure OpenAI API Version
    # API version for Azure OpenAI services
    AOAI_API_VERSION: str = "2025-04-01-preview"

    # File storage paths
    UPLOAD_DIR: str = "./static/uploads"
    IMAGE_DIR: str = "./static/images"
    VIDEO_DIR: str = "./static/videos"

    # GPT-Image-1 Default Settings
    GPT_IMAGE_DEFAULT_SIZE: str = "1024x1024"
    GPT_IMAGE_DEFAULT_QUALITY: str = "high"
    GPT_IMAGE_DEFAULT_FORMAT: str = "PNG"
    GPT_IMAGE_ALLOW_TRANSPARENT: bool = True
    # Max file size in MB for image uploads
    GPT_IMAGE_MAX_FILE_SIZE_MB: int = 25

    @validator('CORS_ALLOWED_ORIGINS')
    def validate_cors_origins(cls, v):
        """Validate CORS origins configuration to prevent InvalidXmlNodeValue errors"""
        if v == "*":
            return v
        
        # Split and clean origins
        origins = [origin.strip() for origin in v.split(",") if origin.strip()]
        
        # Check if wildcard is mixed with specific origins
        if "*" in origins and len(origins) > 1:
            raise ValueError(
                "Cannot mix wildcard '*' with specific origins in CORS configuration. "
                "Use either '*' alone for all origins, or specify individual origins without '*'."
            )
        
        # Validate origin format (basic URL validation)
        for origin in origins:
            if origin != "*" and not (origin.startswith("http://") or origin.startswith("https://")):
                raise ValueError(f"Invalid origin format: {origin}. Origins must start with http:// or https://")
        
        return v

    class Config:
        # Look for .env file in project root (parent of backend directory)
        env_file = str(Path(__file__).parent.parent.parent / ".env")
        env_file_encoding = "utf-8"
        case_sensitive = True
        extra = Extra.allow


settings = Settings()
