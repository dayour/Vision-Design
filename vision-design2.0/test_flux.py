#!/usr/bin/env python
"""Test Flux client directly"""
import sys
import os
import pytest

pytest.skip("Flux client smoke test is disabled during automated test runs", allow_module_level=True)

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from backend.core.config import settings
from backend.core.flux_client import FluxClient

print(f"FLUX_MODEL_PROVIDER: {settings.FLUX_MODEL_PROVIDER}")
print(f"FOUNDRY_API_KEY: {settings.FOUNDRY_API_KEY[:20]}..." if settings.FOUNDRY_API_KEY else "Not set")
print(f"FOUNDRY_ENDPOINT: {settings.FOUNDRY_ENDPOINT}")

try:
    client = FluxClient()
    print(f"Flux client initialized successfully with {client.provider} provider")

    # Try to generate a simple image
    print("Attempting to generate test image...")
    result = client.generate_image(
        prompt="a red circle",
        model="flux-pro",
        width=512,
        height=512
    )
    print("Generation request successful!")
    print(f"Result keys: {result.keys()}")

except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
