"""
Verify all fields on the dystudio_visionassets table.
"""
import json
import sys
import os
import requests
from azure.identity import DefaultAzureCredential

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from backend.core.config import settings


def verify_fields():
    """List all attributes on the dystudio_visionassets entity."""
    
    if not settings.DATAVERSE_ENVIRONMENT_URL:
        print(json.dumps({"success": False, "error": "DATAVERSE_ENVIRONMENT_URL not configured"}))
        sys.exit(1)

    print("Verifying fields on dystudio_visionassets table...")
    
    try:
        # Get credentials
        credential = DefaultAzureCredential()
        token = credential.get_token("https://darbotlabs.crm.dynamics.com/.default")
        
        # Query entity metadata
        api_url = f"{settings.DATAVERSE_ENVIRONMENT_URL}/api/data/v{settings.DATAVERSE_API_VERSION}"
        url = f"{api_url}/EntityDefinitions(LogicalName='dystudio_visionassets')/Attributes"
        
        headers = {
            "Authorization": f"Bearer {token.token}",
            "Content-Type": "application/json",
            "OData-MaxVersion": "4.0",
            "OData-Version": "4.0",
            "Accept": "application/json"
        }
        
        params = {
            "$select": "LogicalName,SchemaName,AttributeType"
        }
        
        response = requests.get(url, headers=headers, params=params)
        
        if response.status_code == 200:
            data = response.json()
            attributes = data.get("value", [])
            
            # Filter for custom dystudio fields
            dystudio_fields = [
                attr for attr in attributes 
                if attr.get("LogicalName", "").startswith("dystudio_")
            ]
            
            print(f"\nFound {len(dystudio_fields)} dystudio_ fields:")
            for attr in sorted(dystudio_fields, key=lambda x: x.get("LogicalName", "")):
                logical_name = attr.get("LogicalName")
                attr_type = attr.get("AttributeType")
                print(f"  - {logical_name} ({attr_type})")
            
            # Check specifically for image_data field
            image_data_field = next(
                (attr for attr in attributes if attr.get("LogicalName") == "dystudio_image_data"),
                None
            )
            
            if image_data_field:
                print(f"\n✓ dystudio_image_data field EXISTS:")
                print(json.dumps(image_data_field, indent=2))
            else:
                print("\n✗ dystudio_image_data field NOT FOUND")
                
        else:
            print(json.dumps({
                "success": False,
                "error": f"Failed to query entity: {response.status_code}",
                "details": response.text
            }, indent=2))
            sys.exit(1)
            
    except Exception as e:
        print(json.dumps({"success": False, "error": str(e)}, indent=2))
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    verify_fields()
