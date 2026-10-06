"""
Add the dystudio_image_data field to the dystudio_visionassets table.
This field will store base64-encoded image data directly in Dataverse.

Usage:
    python backend/tools/add_image_data_field.py
"""
import json
import sys
import os
import requests
from azure.identity import DefaultAzureCredential

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from backend.core.config import settings


def add_image_data_field():
    """Add the dystudio_image_data field to the vision assets table."""
    
    if not settings.DATAVERSE_ENVIRONMENT_URL:
        print(json.dumps({"success": False, "error": "DATAVERSE_ENVIRONMENT_URL not configured"}))
        sys.exit(1)

    print("Adding dystudio_image_data field to dystudio_visionassets table...")
    
    try:
        # Get credentials
        credential = DefaultAzureCredential()
        token = credential.get_token("https://darbotlabs.crm.dynamics.com/.default")
        
        # Define the attribute metadata for a Multiple Lines of Text (Memo) field
        attribute_metadata = {
            "@odata.type": "Microsoft.Dynamics.CRM.MemoAttributeMetadata",
            "AttributeType": "Memo",
            "AttributeTypeName": {"Value": "MemoType"},
            "Description": {
                "@odata.type": "Microsoft.Dynamics.CRM.Label",
                "LocalizedLabels": [
                    {
                        "@odata.type": "Microsoft.Dynamics.CRM.LocalizedLabel",
                        "Label": "Base64-encoded image data",
                        "LanguageCode": 1033
                    }
                ]
            },
            "DisplayName": {
                "@odata.type": "Microsoft.Dynamics.CRM.Label",
                "LocalizedLabels": [
                    {
                        "@odata.type": "Microsoft.Dynamics.CRM.LocalizedLabel",
                        "Label": "Image Data",
                        "LanguageCode": 1033
                    }
                ]
            },
            "RequiredLevel": {
                "Value": "None",
                "CanBeChanged": True,
                "ManagedPropertyLogicalName": "canmodifyrequirementlevelsettings"
            },
            "SchemaName": "dystudio_image_data",
            "ImeMode": "Auto",
            "MaxLength": 1048576  # Maximum size for Memo field (1MB)
        }

        # Send POST request to create the attribute
        api_url = f"{settings.DATAVERSE_ENVIRONMENT_URL}/api/data/v{settings.DATAVERSE_API_VERSION}"
        url = f"{api_url}/EntityDefinitions(LogicalName='dystudio_visionassets')/Attributes"
        
        headers = {
            "Authorization": f"Bearer {token.token}",
            "Content-Type": "application/json",
            "OData-MaxVersion": "4.0",
            "OData-Version": "4.0",
            "Accept": "application/json"
        }
        
        response = requests.post(url, headers=headers, json=attribute_metadata)
        
        if response.status_code == 204:
            print(json.dumps({
                "success": True,
                "message": "Successfully added dystudio_image_data field",
                "field_name": "dystudio_image_data",
                "max_length": 1048576
            }, indent=2))
        else:
            error_detail = response.text
            print(json.dumps({
                "success": False,
                "error": f"Failed to create field: {response.status_code}",
                "details": error_detail
            }, indent=2))
            sys.exit(1)
            
    except Exception as e:
        print(json.dumps({"success": False, "error": str(e)}, indent=2))
        sys.exit(1)


if __name__ == "__main__":
    add_image_data_field()
