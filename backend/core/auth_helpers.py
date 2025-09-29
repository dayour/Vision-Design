"""
Authentication helpers for Vision Design prototype.
Provides integration with Azure CLI, PAC CLI, Connect-MGGraph, and GitHub.
"""

import subprocess
import logging
import json
import os
from typing import Dict, Optional, Any
from azure.identity import AzureCliCredential, DefaultAzureCredential
from .config import settings

logger = logging.getLogger(__name__)


class AuthenticationHelper:
    """
    Helper class for managing various authentication methods used by Vision Design.
    """

    def __init__(self):
        """Initialize authentication helper"""
        self.az_credential = None
        self.pac_authenticated = False
        self.github_authenticated = False
        self.mg_authenticated = False

    def check_azure_cli_auth(self) -> Dict[str, Any]:
        """
        Check Azure CLI authentication status
        
        Returns:
            Dictionary with authentication status and account info
        """
        try:
            # Check if Azure CLI is installed
            result = subprocess.run(
                ["az", "--version"], 
                capture_output=True, 
                text=True, 
                timeout=10
            )
            
            if result.returncode != 0:
                return {
                    "authenticated": False,
                    "error": "Azure CLI not installed or not available"
                }
            
            # Check authentication status
            result = subprocess.run(
                ["az", "account", "show"], 
                capture_output=True, 
                text=True, 
                timeout=10
            )
            
            if result.returncode == 0:
                account_info = json.loads(result.stdout)
                self.az_credential = AzureCliCredential()
                return {
                    "authenticated": True,
                    "account": {
                        "name": account_info.get("user", {}).get("name"),
                        "subscription": account_info.get("name"),
                        "subscription_id": account_info.get("id"),
                        "tenant_id": account_info.get("tenantId")
                    }
                }
            else:
                return {
                    "authenticated": False,
                    "error": "Not logged in to Azure CLI. Run 'az login' to authenticate."
                }
                
        except subprocess.TimeoutExpired:
            return {
                "authenticated": False,
                "error": "Azure CLI command timed out"
            }
        except Exception as e:
            logger.error(f"Error checking Azure CLI authentication: {e}")
            return {
                "authenticated": False,
                "error": str(e)
            }

    def check_pac_cli_auth(self) -> Dict[str, Any]:
        """
        Check Power Platform CLI authentication status
        
        Returns:
            Dictionary with authentication status and environment info
        """
        try:
            # Check if PAC CLI is installed
            result = subprocess.run(
                ["pac", "--version"], 
                capture_output=True, 
                text=True, 
                timeout=10
            )
            
            if result.returncode != 0:
                return {
                    "authenticated": False,
                    "error": "Power Platform CLI not installed. Install with 'pac install latest'"
                }
            
            # Check authentication status
            result = subprocess.run(
                ["pac", "org", "who"], 
                capture_output=True, 
                text=True, 
                timeout=15
            )
            
            if result.returncode == 0:
                self.pac_authenticated = True
                # Parse the output to extract environment info
                output = result.stdout.strip()
                return {
                    "authenticated": True,
                    "environment_info": output
                }
            else:
                return {
                    "authenticated": False,
                    "error": "Not connected to Power Platform. Run 'pac auth create --url https://your-env.crm.dynamics.com/'"
                }
                
        except subprocess.TimeoutExpired:
            return {
                "authenticated": False,
                "error": "PAC CLI command timed out"
            }
        except Exception as e:
            logger.error(f"Error checking PAC CLI authentication: {e}")
            return {
                "authenticated": False,
                "error": str(e)
            }

    def check_microsoft_graph_auth(self) -> Dict[str, Any]:
        """
        Check Microsoft Graph PowerShell authentication status
        
        Returns:
            Dictionary with authentication status
        """
        try:
            # Check if Connect-MgGraph is available (requires PowerShell)
            result = subprocess.run(
                ["pwsh", "-Command", "Get-Module -ListAvailable Microsoft.Graph.Authentication"],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode != 0 or not result.stdout.strip():
                return {
                    "authenticated": False,
                    "error": "Microsoft Graph PowerShell module not installed. Install with 'Install-Module Microsoft.Graph'"
                }
            
            # Check if connected
            result = subprocess.run(
                ["pwsh", "-Command", "Get-MgContext | ConvertTo-Json"],
                capture_output=True,
                text=True,
                timeout=15
            )
            
            if result.returncode == 0 and result.stdout.strip():
                try:
                    context = json.loads(result.stdout)
                    if context and context.get("Account"):
                        self.mg_authenticated = True
                        return {
                            "authenticated": True,
                            "context": {
                                "account": context.get("Account"),
                                "scopes": context.get("Scopes", []),
                                "tenant_id": context.get("TenantId")
                            }
                        }
                except json.JSONDecodeError:
                    pass
                    
            return {
                "authenticated": False,
                "error": "Not connected to Microsoft Graph. Run 'Connect-MgGraph' in PowerShell"
            }
            
        except subprocess.TimeoutExpired:
            return {
                "authenticated": False,
                "error": "Microsoft Graph command timed out"
            }
        except Exception as e:
            logger.error(f"Error checking Microsoft Graph authentication: {e}")
            return {
                "authenticated": False,
                "error": str(e)
            }

    def check_github_auth(self) -> Dict[str, Any]:
        """
        Check GitHub CLI authentication status
        
        Returns:
            Dictionary with authentication status and user info
        """
        try:
            # First check if we have a GitHub token in settings
            if settings.GITHUB_TOKEN:
                return {
                    "authenticated": True,
                    "method": "token",
                    "note": "Using GITHUB_TOKEN from environment"
                }
            
            # Check if GitHub CLI is installed
            result = subprocess.run(
                ["gh", "--version"], 
                capture_output=True, 
                text=True, 
                timeout=10
            )
            
            if result.returncode != 0:
                return {
                    "authenticated": False,
                    "error": "GitHub CLI not installed. Install from https://cli.github.com/"
                }
            
            # Check authentication status
            result = subprocess.run(
                ["gh", "auth", "status"], 
                capture_output=True, 
                text=True, 
                timeout=10
            )
            
            if result.returncode == 0:
                self.github_authenticated = True
                return {
                    "authenticated": True,
                    "method": "cli",
                    "status_info": result.stdout.strip()
                }
            else:
                return {
                    "authenticated": False,
                    "error": "Not logged in to GitHub CLI. Run 'gh auth login' to authenticate."
                }
                
        except subprocess.TimeoutExpired:
            return {
                "authenticated": False,
                "error": "GitHub CLI command timed out"
            }
        except Exception as e:
            logger.error(f"Error checking GitHub authentication: {e}")
            return {
                "authenticated": False,
                "error": str(e)
            }

    def get_authentication_status(self) -> Dict[str, Any]:
        """
        Get comprehensive authentication status for all services
        
        Returns:
            Dictionary with status for all authentication methods
        """
        return {
            "azure_cli": self.check_azure_cli_auth(),
            "power_platform": self.check_pac_cli_auth(),
            "microsoft_graph": self.check_microsoft_graph_auth(),
            "github": self.check_github_auth()
        }

    def authenticate_to_azure(self) -> bool:
        """
        Guide user through Azure CLI authentication
        
        Returns:
            True if successful, False otherwise
        """
        try:
            logger.info("Starting Azure CLI authentication...")
            result = subprocess.run(
                ["az", "login"],
                timeout=300  # 5 minutes for interactive login
            )
            
            if result.returncode == 0:
                logger.info("Azure CLI authentication successful")
                return True
            else:
                logger.error("Azure CLI authentication failed")
                return False
                
        except Exception as e:
            logger.error(f"Error during Azure CLI authentication: {e}")
            return False

    def authenticate_to_power_platform(self, environment_url: str) -> bool:
        """
        Guide user through Power Platform authentication
        
        Args:
            environment_url: The Dataverse environment URL
            
        Returns:
            True if successful, False otherwise
        """
        try:
            logger.info(f"Starting Power Platform authentication to {environment_url}...")
            result = subprocess.run(
                ["pac", "auth", "create", "--url", environment_url],
                timeout=300  # 5 minutes for interactive login
            )
            
            if result.returncode == 0:
                logger.info("Power Platform authentication successful")
                return True
            else:
                logger.error("Power Platform authentication failed")
                return False
                
        except Exception as e:
            logger.error(f"Error during Power Platform authentication: {e}")
            return False

    def get_simplified_setup_instructions(self) -> Dict[str, str]:
        """
        Get simplified setup instructions for each authentication method
        
        Returns:
            Dictionary with setup instructions
        """
        return {
            "azure_cli": {
                "install": "Install: https://docs.microsoft.com/en-us/cli/azure/install-azure-cli",
                "authenticate": "Run: az login",
                "verify": "Run: az account show"
            },
            "power_platform": {
                "install": "Run: pac install latest",
                "authenticate": "Run: pac auth create --url https://your-env.crm.dynamics.com/",
                "verify": "Run: pac org who"
            },
            "microsoft_graph": {
                "install": "In PowerShell: Install-Module Microsoft.Graph -Scope CurrentUser",
                "authenticate": "In PowerShell: Connect-MgGraph -Scopes 'User.Read'",
                "verify": "In PowerShell: Get-MgContext"
            },
            "github": {
                "install": "Install: https://cli.github.com/",
                "authenticate": "Run: gh auth login",
                "verify": "Run: gh auth status"
            }
        }


# Global instance
auth_helper = AuthenticationHelper()

def get_auth_helper() -> AuthenticationHelper:
    """Get the global authentication helper instance"""
    return auth_helper