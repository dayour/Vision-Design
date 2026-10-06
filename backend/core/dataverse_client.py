"""
Microsoft Dataverse client for Vision Design prototype.
Provides rich metadata storage and indexing capabilities for generated images.
"""

import logging
import json
from typing import Dict, List, Optional, Any
from datetime import datetime
import requests
from azure.identity import DefaultAzureCredential, ClientSecretCredential
from .config import settings
from .pac_cli import try_acquire_pac_cli_token

logger = logging.getLogger(__name__)


class DataverseClient:
    """
    Client for Microsoft Dataverse integration.
    Provides rich relational storage for image metadata, tags, and indexing.
    """

    def __init__(self):
        """Initialize Dataverse client with authentication"""
        self.environment_url = settings.DATAVERSE_ENVIRONMENT_URL
        self.table_name = settings.DATAVERSE_TABLE_NAME
        self.client_id = settings.DATAVERSE_CLIENT_ID
        self.client_secret = settings.DATAVERSE_CLIENT_SECRET
        
        if not self.environment_url:
            logger.warning("Dataverse environment URL not configured")
            self.enabled = False
            return
            
        self.enabled = True
        self.api_url = f"{self.environment_url.rstrip('/')}/api/data/v9.2"
        self.token = None
        self.token_expires = None
        
        # Initialize authentication
        try:
            self._authenticate()
            logger.info("Dataverse client initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Dataverse client: {e}")
            self.enabled = False

    def _authenticate(self) -> str:
        """Authenticate and get access token for Dataverse"""
        if not self.enabled:
            return None
            
        try:
            pac_token = None
            if settings.DATAVERSE_USE_PAC_AUTH:
                pac_token = try_acquire_pac_cli_token(
                    environment_url=self.environment_url,
                    profile_hint=settings.DATAVERSE_PAC_PROFILE,
                )
            if pac_token:
                self.token = pac_token.access_token
                self.token_expires = int(pac_token.expires_on.timestamp())
                return self.token

            # Use client credentials flow for service-to-service authentication
            if self.client_id and self.client_secret:
                credential = ClientSecretCredential(
                    tenant_id=self._extract_tenant_from_url(),
                    client_id=self.client_id,
                    client_secret=self.client_secret
                )
            else:
                # Fall back to default credential (managed identity, Azure CLI, etc.)
                credential = DefaultAzureCredential(exclude_interactive_browser_credential=True)
            
            # Get token for Dataverse
            token_result = credential.get_token(f"{self.environment_url}/.default")
            self.token = token_result.token
            self.token_expires = token_result.expires_on
            
            return self.token
            
        except Exception as e:
            logger.error(f"Failed to authenticate with Dataverse: {e}")
            raise

    def _extract_tenant_from_url(self) -> str:
        """Extract tenant ID from Dataverse environment URL"""
        # For now, we'll use a common tenant or require it to be set separately
        # In production, this would be properly configured
        return "common"  # This would need to be properly configured

    def _get_headers(self) -> Dict[str, str]:
        """Get authenticated headers for API requests"""
        if not self.token:
            self._authenticate()
            
        return {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
            "OData-MaxVersion": "4.0",
            "OData-Version": "4.0"
        }

    def _ensure_table_exists(self) -> bool:
        """Ensure the vision assets table exists in Dataverse"""
        if not self.enabled:
            return False
            
        try:
            # Check if table exists
            response = requests.get(
                f"{self.api_url}/EntityDefinitions",
                headers=self._get_headers(),
                params={"$filter": f"LogicalName eq '{self.table_name}'"}
            )
            
            if response.status_code == 200:
                entities = response.json().get("value", [])
                if entities:
                    logger.info(f"Dataverse table '{self.table_name}' exists")
                    return True
                    
            # Table doesn't exist, we would need to create it
            # For now, we'll log and return False - table creation requires admin permissions
            logger.warning(f"Dataverse table '{self.table_name}' not found. Please create it manually or ensure proper permissions.")
            return False
            
        except Exception as e:
            logger.error(f"Error checking Dataverse table existence: {e}")
            return False

    def _create_entity(self, schema_name: str, display_name: str, collection_name: str, ownership: str = "UserOwned") -> Optional[str]:
        """Create an entity (table) in Dataverse using the Web API.

        Returns the created entity logical name or None on failure.
        """
        try:
            body = {
                "SchemaName": schema_name,
                "DisplayName": {"LocalizedLabels": [{"Label": display_name, "LanguageCode": 1033}]},
                "DisplayCollectionName": {"LocalizedLabels": [{"Label": collection_name, "LanguageCode": 1033}]},
                "OwnershipType": ownership,
                "IsActivity": False
            }

            response = requests.post(
                f"{self.api_url}/EntityDefinitions",
                headers=self._get_headers(),
                json=body
            )

            if response.status_code in (200, 201, 204):
                logger.info(f"Created entity '{schema_name}' successfully.")
                return schema_name
            else:
                logger.error(f"Failed to create entity '{schema_name}': {response.status_code} - {response.text}")
                return None
        except Exception as e:
            logger.error(f"Exception while creating entity '{schema_name}': {e}")
            return None

    def _create_string_attribute(self, entity_logical_name: str, schema_name: str, display_name: str, max_length: int = 100) -> bool:
        """Create a single-line string attribute on an entity."""
        try:
            body = {
                "@odata.type": "Microsoft.Dynamics.CRM.StringAttributeMetadata",
                "SchemaName": schema_name,
                "DisplayName": {"LocalizedLabels": [{"Label": display_name, "LanguageCode": 1033}]},
                "RequiredLevel": {"Value": "None"},
                "MaxLength": max_length
            }

            response = requests.post(
                f"{self.api_url}/AttributeDefinitions",
                headers=self._get_headers(),
                json={
                    **body,
                    # Attach the attribute to the specified entity
                    "EntityLogicalName": entity_logical_name
                }
            )

            if response.status_code in (200, 201, 204):
                logger.info(f"Created string attribute '{schema_name}' on '{entity_logical_name}'")
                return True
            else:
                logger.error(f"Failed to create attribute '{schema_name}': {response.status_code} - {response.text}")
                return False

        except Exception as e:
            logger.error(f"Exception while creating attribute '{schema_name}': {e}")
            return False

    def create_tables_if_missing(self) -> Dict[str, Any]:
        """Attempt to create the vision assets and generation history tables (and basic attributes).

        This operation requires sufficient Dataverse privileges and may fail in non-admin accounts.
        The method will try to create minimal tables and attributes and return a summary of results.
        """
        results = {
            "vision_assets": {"created": False, "details": None},
            "generation_history": {"created": False, "details": None}
        }

        if not self.enabled:
            results["error"] = "Dataverse client not enabled or not configured"
            return results

        try:
            # First, check whether vision assets table already exists
            exists = self._ensure_table_exists()
            if exists:
                results["vision_assets"]["created"] = False
                results["vision_assets"]["details"] = "Already exists"
            else:
                schema_name = self.table_name.replace("_", "_").title().replace("Cr6f1", "cr6f1_")
                # Use a predictable schema name like cr6f1_VisionAsset
                schema_name = "cr6f1_VisionAsset"
                created = self._create_entity(schema_name, "Vision Asset", "Vision Assets")
                if created:
                    # Create basic attributes
                    self._create_string_attribute(self.table_name, "cr6f1_name", "Name", max_length=150)
                    self._create_string_attribute(self.table_name, "cr6f1_imageurl", "Image URL", max_length=1000)
                    self._create_string_attribute(self.table_name, "cr6f1_prompt", "Prompt", max_length=2000)
                    self._create_string_attribute(self.table_name, "cr6f1_model", "Model", max_length=200)
                    results["vision_assets"]["created"] = True
                    results["vision_assets"]["details"] = f"Created entity {schema_name} and basic attributes"
                else:
                    results["vision_assets"]["details"] = "Failed to create entity (check permissions)"

            # Now attempt generation history table
            history_logical = f"{self.table_name}_generationhistory"
            # Check existence
            response = requests.get(
                f"{self.api_url}/EntityDefinitions",
                headers=self._get_headers(),
                params={"$filter": f"LogicalName eq '{history_logical}'"}
            )
            if response.status_code == 200 and response.json().get("value", []):
                results["generation_history"]["created"] = False
                results["generation_history"]["details"] = "Already exists"
            else:
                schema_name = "cr6f1_GenerationHistory"
                created = self._create_entity(schema_name, "Generation History", "Generation Histories")
                if created:
                    self._create_string_attribute(history_logical, "cr6f1_prompt", "Prompt", max_length=2000)
                    self._create_string_attribute(history_logical, "cr6f1_model", "Model", max_length=200)
                    # Note: creating lookups and relationships requires more complex metadata calls; skip for now
                    results["generation_history"]["created"] = True
                    results["generation_history"]["details"] = f"Created entity {schema_name} with basic attributes"
                else:
                    results["generation_history"]["details"] = "Failed to create generation history entity (check permissions)"

        except Exception as e:
            logger.error(f"Error while attempting to create tables: {e}")
            results["error"] = str(e)

        return results

    def store_image_metadata(self, metadata: Dict[str, Any]) -> Optional[str]:
        """
        Store image metadata in Dataverse
        
        Args:
            metadata: Dictionary containing image metadata
            
        Returns:
            Record ID if successful, None otherwise
        """
        if not self.enabled:
            logger.warning("Dataverse client not enabled")
            return None
            
        try:
            # Prepare data for Dataverse
            dataverse_record = {
                "cr6f1_name": metadata.get("filename", "Unknown"),
                "cr6f1_prompt": metadata.get("prompt", ""),
                "cr6f1_model": metadata.get("model", ""),
                "cr6f1_generateddate": datetime.utcnow().isoformat() + "Z",
                "cr6f1_imageurl": metadata.get("url", ""),
                "cr6f1_filehash": metadata.get("file_hash", ""),
                "cr6f1_width": metadata.get("width", 0),
                "cr6f1_height": metadata.get("height", 0),
                "cr6f1_filesize": metadata.get("file_size", 0),
                "cr6f1_tags": json.dumps(metadata.get("tags", [])),
                "cr6f1_quality": metadata.get("quality", ""),
                "cr6f1_seed": metadata.get("seed", 0) if metadata.get("seed") else None,
                "cr6f1_modelversion": metadata.get("model_version", ""),
                "cr6f1_generationsettings": json.dumps(metadata.get("generation_settings", {}))
            }
            
            # Remove None values
            dataverse_record = {k: v for k, v in dataverse_record.items() if v is not None}
            
            # Create record
            response = requests.post(
                f"{self.api_url}/{self.table_name}",
                headers=self._get_headers(),
                json=dataverse_record
            )
            
            if response.status_code == 201:
                # Extract record ID from response headers
                location = response.headers.get("OData-EntityId", "")
                record_id = location.split("(")[-1].rstrip(")")
                logger.info(f"Successfully stored image metadata in Dataverse: {record_id}")
                return record_id
            else:
                logger.error(f"Failed to store image metadata in Dataverse: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"Error storing image metadata in Dataverse: {e}")
            return None

    def query_images(self, filter_params: Optional[Dict[str, Any]] = None, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Query images from Dataverse with optional filtering
        
        Args:
            filter_params: Dictionary of filter parameters
            limit: Maximum number of records to return
            
        Returns:
            List of image metadata records
        """
        if not self.enabled:
            return []
            
        try:
            # Build OData query
            params = {
                "$top": str(limit),
                "$orderby": "cr6f1_generateddate desc"
            }
            
            # Add filters if provided
            if filter_params:
                filters = []
                for key, value in filter_params.items():
                    if key == "model" and value:
                        filters.append(f"cr6f1_model eq '{value}'")
                    elif key == "prompt_contains" and value:
                        filters.append(f"contains(cr6f1_prompt, '{value}')")
                    elif key == "date_from" and value:
                        filters.append(f"cr6f1_generateddate ge {value}")
                    elif key == "date_to" and value:
                        filters.append(f"cr6f1_generateddate le {value}")
                        
                if filters:
                    params["$filter"] = " and ".join(filters)
            
            response = requests.get(
                f"{self.api_url}/{self.table_name}",
                headers=self._get_headers(),
                params=params
            )
            
            if response.status_code == 200:
                records = response.json().get("value", [])
                
                # Convert to standard format
                result = []
                for record in records:
                    result.append({
                        "id": record.get("cr6f1_visionassetid"),
                        "filename": record.get("cr6f1_name"),
                        "prompt": record.get("cr6f1_prompt"),
                        "model": record.get("cr6f1_model"),
                        "generated_date": record.get("cr6f1_generateddate"),
                        "url": record.get("cr6f1_imageurl"),
                        "file_hash": record.get("cr6f1_filehash"),
                        "width": record.get("cr6f1_width"),
                        "height": record.get("cr6f1_height"),
                        "file_size": record.get("cr6f1_filesize"),
                        "tags": json.loads(record.get("cr6f1_tags", "[]")),
                        "quality": record.get("cr6f1_quality"),
                        "seed": record.get("cr6f1_seed"),
                        "model_version": record.get("cr6f1_modelversion"),
                        "generation_settings": json.loads(record.get("cr6f1_generationsettings", "{}"))
                    })
                
                return result
            else:
                logger.error(f"Failed to query images from Dataverse: {response.status_code}")
                return []
                
        except Exception as e:
            logger.error(f"Error querying images from Dataverse: {e}")
            return []

    def update_image_tags(self, record_id: str, tags: List[str]) -> bool:
        """
        Update tags for an image record
        
        Args:
            record_id: Dataverse record ID
            tags: List of tags to set
            
        Returns:
            True if successful, False otherwise
        """
        if not self.enabled:
            return False
            
        try:
            update_data = {
                "cr6f1_tags": json.dumps(tags)
            }
            
            response = requests.patch(
                f"{self.api_url}/{self.table_name}({record_id})",
                headers=self._get_headers(),
                json=update_data
            )
            
            if response.status_code == 204:
                logger.info(f"Successfully updated tags for record {record_id}")
                return True
            else:
                logger.error(f"Failed to update tags: {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"Error updating image tags: {e}")
            return False

    def delete_image_record(self, record_id: str) -> bool:
        """
        Delete an image record from Dataverse
        
        Args:
            record_id: Dataverse record ID
            
        Returns:
            True if successful, False otherwise
        """
        if not self.enabled:
            return False
            
        try:
            response = requests.delete(
                f"{self.api_url}/{self.table_name}({record_id})",
                headers=self._get_headers()
            )
            
            if response.status_code == 204:
                logger.info(f"Successfully deleted record {record_id}")
                return True
            else:
                logger.error(f"Failed to delete record: {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"Error deleting image record: {e}")
            return False


# Global instance
dataverse_client = None

def get_dataverse_client() -> Optional[DataverseClient]:
    """Get the global Dataverse client instance"""
    global dataverse_client
    if dataverse_client is None and settings.DATAVERSE_ENVIRONMENT_URL:
        try:
            dataverse_client = DataverseClient()
        except Exception as e:
            logger.error(f"Failed to initialize Dataverse client: {e}")
            dataverse_client = None
    return dataverse_client
