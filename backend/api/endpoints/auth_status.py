"""
Authentication status endpoint for Vision Design prototype.
Provides status of various CLI and service authentications.
"""

from fastapi import APIRouter
from typing import Dict, Any
import logging
from backend.core.auth_helpers import get_auth_helper
from backend.core.dataverse_client import get_dataverse_client

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/auth/status")
async def get_authentication_status() -> Dict[str, Any]:
    """
    Get comprehensive authentication status for all services
    
    Returns:
        Dictionary with authentication status for all services
    """
    try:
        auth_helper = get_auth_helper()
        status = auth_helper.get_authentication_status()
        
        # Add Dataverse status
        dataverse_client = get_dataverse_client()
        status["dataverse"] = {
            "enabled": dataverse_client.enabled if dataverse_client else False,
            "configured": bool(dataverse_client and dataverse_client.environment_url)
        }
        
        return {
            "success": True,
            "authentication_status": status
        }
        
    except Exception as e:
        logger.error(f"Error getting authentication status: {e}")
        return {
            "success": False,
            "error": str(e),
            "authentication_status": {}
        }


@router.get("/auth/setup-instructions") 
async def get_setup_instructions() -> Dict[str, Any]:
    """
    Get simplified setup instructions for authentication methods
    
    Returns:
        Dictionary with setup instructions for each service
    """
    try:
        auth_helper = get_auth_helper()
        instructions = auth_helper.get_simplified_setup_instructions()
        
        return {
            "success": True,
            "setup_instructions": instructions
        }
        
    except Exception as e:
        logger.error(f"Error getting setup instructions: {e}")
        return {
            "success": False,
            "error": str(e),
            "setup_instructions": {}
        }


@router.post("/auth/azure/login")
async def initiate_azure_login() -> Dict[str, Any]:
    """
    Initiate Azure CLI authentication (for development environments)
    
    Returns:
        Status of authentication attempt
    """
    try:
        auth_helper = get_auth_helper()
        success = auth_helper.authenticate_to_azure()
        
        return {
            "success": success,
            "message": "Azure authentication completed" if success else "Azure authentication failed"
        }
        
    except Exception as e:
        logger.error(f"Error during Azure authentication: {e}")
        return {
            "success": False,
            "error": str(e),
            "message": "Azure authentication error"
        }


@router.post("/auth/power-platform/connect")
async def connect_power_platform(environment_url: str) -> Dict[str, Any]:
    """
    Connect to Power Platform environment
    
    Args:
        environment_url: The Dataverse environment URL
        
    Returns:
        Status of connection attempt
    """
    try:
        auth_helper = get_auth_helper()
        success = auth_helper.authenticate_to_power_platform(environment_url)
        
        return {
            "success": success,
            "message": "Power Platform connection completed" if success else "Power Platform connection failed"
        }
        
    except Exception as e:
        logger.error(f"Error connecting to Power Platform: {e}")
        return {
            "success": False,
            "error": str(e),
            "message": "Power Platform connection error"
        }