"""
Debug script to fetch asset metadata directly using DataverseService and print full exception details.
"""
import sys
import os
import traceback

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from backend.core.dataverse_service import DataverseService, DataverseError

ASSET_ID = "65f74123-509f-f011-bbd2-000d3a59e754"

try:
    svc = DataverseService()
    print("Dataverse service initialized")
    metadata = svc.get_asset_metadata(ASSET_ID)
    print("Metadata:")
    print(metadata)
except DataverseError as e:
    print("DataverseError:")
    print(str(e))
    traceback.print_exc()
except Exception as e:
    print("General exception:")
    print(str(e))
    traceback.print_exc()
