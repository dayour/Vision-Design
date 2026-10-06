"""
Utility script to create minimal Dataverse tables for the Vision Design prototype.
This script re-uses the project's Dataverse client and attempts to create two minimal tables
(vision assets and generation history) along with a small set of basic attributes.

Usage:
    python backend/tools/create_dataverse_tables.py

Notes:
 - This operation requires Dataverse administrative privileges. If you run this with a
   user account that lacks sufficient permissions, creation will fail and the script
   will print diagnostic messages.
 - No secrets are written to disk by this script.
"""
import json
import sys
from backend.core.dataverse_client import get_dataverse_client


def main():
    client = get_dataverse_client()
    if not client:
        print(json.dumps({"success": False, "error": "Dataverse client not initialized"}))
        sys.exit(1)

    print("Attempting to create Dataverse tables if missing. This may require admin permissions...")
    result = client.create_tables_if_missing()
    print(json.dumps({"success": True, "result": result}, indent=2))


if __name__ == "__main__":
    main()
