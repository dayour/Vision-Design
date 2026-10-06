"""
Test script to verify Dataverse connection and basic operations
"""
import sys
import os

# Ensure project root is on sys.path for backend imports
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import pytest
from backend.core.dataverse_service import DataverseService, DataverseError
from backend.core.config import settings
import json
pytestmark = pytest.mark.skipif(
    os.getenv('ENABLE_DATAVERSE_TESTS') is None,
    reason='Dataverse integration tests disabled by default; set ENABLE_DATAVERSE_TESTS=1 to run.'
)


def test_health_check():
    """Test Dataverse health check"""
    print("Testing Dataverse Health Check...")
    print(f"Environment URL: {settings.DATAVERSE_ENVIRONMENT_URL}")
    print(f"Use Managed Identity: {settings.DATAVERSE_USE_MANAGED_IDENTITY}")
    print(f"Tables: {settings.DATAVERSE_TABLE_VISIONASSETS}, {settings.DATAVERSE_TABLE_ASSETTAGS}, {settings.DATAVERSE_TABLE_GENERATIONHISTORY}")
    print()
    
    try:
        service = DataverseService()
        print("✅ DataverseService initialized successfully")

        # Test health check
        health = service.health_check()
        print(f"✅ Health check: {health['status']}")
        print(f"   User ID: {health.get('user_id')}")
        print(f"   Organization ID: {health.get('organization_id')}")
        print()

        assert isinstance(health, dict)
        assert "status" in health
    except DataverseError as e:
        pytest.skip(f"Dataverse not available: {e}")
    except Exception as e:
        pytest.fail(f"Unexpected error during health check: {e}")


def test_query_assets():
    """Test querying assets"""
    print("Testing Query Assets...")
    
    try:
        service = DataverseService()

        # Query first 5 assets
        result = service.query_assets(limit=5, offset=0)
        print(f"✅ Query successful")
        print(f"   Total assets: {result.get('total')}")
        print(f"   Retrieved: {len(result.get('items', []))} assets")

        if result.get('items'):
            print(f"   First asset ID: {result['items'][0].get('id')}")
            print(f"   First asset media_type: {result['items'][0].get('media_type')}")
        print()

        assert isinstance(result, dict)
        assert "items" in result
    except DataverseError as e:
        pytest.skip(f"Dataverse not available: {e}")
    except Exception as e:
        pytest.fail(f"Unexpected error during query assets: {e}")


def test_list_tags():
    """Test listing tags"""
    print("Testing List Tags...")
    
    try:
        service = DataverseService()

        # Query tags table directly
        params = {
            "$select": "dystudio_assettagid,dystudio_name,dystudio_category",
            "$top": 5
        }

        response = service._request("GET", service._tags_table, params=params)
        records = response.get("value", []) if response else []

        print(f"✅ Tag query successful")
        print(f"   Retrieved: {len(records)} tags")

        for tag in records:
            print(f"   - {tag.get('dystudio_name')} (ID: {tag.get('dystudio_assettagid')})")
        print()

        assert isinstance(records, list)
    except DataverseError as e:
        pytest.skip(f"Dataverse not available or tags not found: {e}")
    except Exception as e:
        pytest.fail(f"Unexpected error during list tags: {e}")


if __name__ == "__main__":
    print("=" * 60)
    print("DATAVERSE CONNECTION TEST")
    print("=" * 60)
    print()
    
    results = []
    
    # Run tests
    results.append(("Health Check", test_health_check()))
    results.append(("Query Assets", test_query_assets()))
    results.append(("List Tags", test_list_tags()))
    
    # Summary
    print("=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    
    for test_name, passed in results:
        status = "✅ PASSED" if passed else "❌ FAILED"
        print(f"{test_name}: {status}")
    
    print()
    all_passed = all(result[1] for result in results)
    
    if all_passed:
        print("🎉 All tests passed! Dataverse integration is working correctly.")
        sys.exit(0)
    else:
        print("⚠️  Some tests failed. Please check the configuration and errors above.")
        sys.exit(1)
