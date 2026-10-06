from fastapi import APIRouter
from backend.core.config import settings
from typing import Dict, List

router = APIRouter()


@router.get("/env/status", response_model=Dict[str, List[str]])
def env_status():
    """Return which environment variables are configured versus missing."""
    use_managed_identity = bool(getattr(settings, "DATAVERSE_USE_MANAGED_IDENTITY", False))

    required_vars = ["DATAVERSE_ENVIRONMENT_URL"]
    optional_vars = [
        "SORA_AOAI_RESOURCE",
        "SORA_AOAI_API_KEY",
        "SORA_DEPLOYMENT",
        "LLM_AOAI_RESOURCE",
        "LLM_DEPLOYMENT",
        "LLM_AOAI_API_KEY",
        "IMAGEGEN_AOAI_RESOURCE",
        "IMAGEGEN_DEPLOYMENT",
        "IMAGEGEN_AOAI_API_KEY",
        "FOUNDRY_API_KEY",
        "FOUNDRY_ENDPOINT",
        "FOUNDRY_DEPLOYMENT_FLUX_PRO",
        "FOUNDRY_FLUX_PRO_ENDPOINT",
        "FOUNDRY_DEPLOYMENT_FLUX_KONTEXT",
        "FOUNDRY_FLUX_KONTEXT_ENDPOINT",
        "BFL_API_KEY",
        "FLUX_MODEL_PROVIDER",
    ]

    if use_managed_identity:
        optional_vars.extend([
            "DATAVERSE_CLIENT_ID",
            "DATAVERSE_CLIENT_SECRET",
            "AZURE_TENANT_ID",
        ])
    else:
        required_vars.extend([
            "DATAVERSE_CLIENT_ID",
            "DATAVERSE_CLIENT_SECRET",
            "AZURE_TENANT_ID",
        ])

    optional_vars = list(dict.fromkeys(optional_vars))

    def is_configured(var_name: str) -> bool:
        if not hasattr(settings, var_name):
            return False
        value = getattr(settings, var_name)
        if isinstance(value, bool):
            return True
        if value is None:
            return False
        if isinstance(value, str):
            return value.strip() != ""
        return True

    set_vars: List[str] = []
    missing_vars: List[str] = []

    for var in required_vars:
        if is_configured(var):
            set_vars.append(var)
        else:
            missing_vars.append(var)

    for var in optional_vars:
        if is_configured(var):
            set_vars.append(var)

    optional_missing = [var for var in optional_vars if var not in set_vars]

    if use_managed_identity or getattr(settings, "DATAVERSE_USE_PAC_AUTH", False):
        suppressed = {"DATAVERSE_CLIENT_ID", "DATAVERSE_CLIENT_SECRET", "AZURE_TENANT_ID"}
        optional_missing = [var for var in optional_missing if var not in suppressed]

    return {
        "set": sorted(set_vars),
        "missing": sorted(missing_vars),
        "optional_missing": sorted(optional_missing),
    }
