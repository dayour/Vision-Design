"""Helpers for reusing Power Platform CLI authentication tokens."""

from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Iterable, Optional

import msal

logger = logging.getLogger(__name__)

try:
    from msal_extensions import (  # type: ignore
        FilePersistence,
        FilePersistenceWithDataProtection,
        PersistedTokenCache,
    )
except ImportError:  # pragma: no cover - optional dependency
    FilePersistence = None  # type: ignore[assignment]
    FilePersistenceWithDataProtection = None  # type: ignore[assignment]
    PersistedTokenCache = None  # type: ignore[assignment]


class PacCliError(Exception):
    """Base exception for PAC CLI authentication helpers."""


class PacCliNotConfiguredError(PacCliError):
    """Raised when no PAC CLI profile is configured for the current user."""


class PacCliAuthError(PacCliError):
    """Raised when PAC CLI authentication data cannot produce a usable token."""


@dataclass
class PacCliToken:
    """Container for an access token minted via PAC CLI credentials."""

    access_token: str
    expires_on: datetime
    username: str
    environment_url: str


class PacCliTokenProvider:
    """Loads previously-acquired PAC CLI tokens from the local cache."""

    _CLIENT_ID_FALLBACKS = (
        "9cee029c-6210-4654-90bb-17e6e9d36617",
        "51f81489-12ee-4a9e-aaae-a2591f45987d",
        "04b07795-8ddb-461a-bbee-02f9e1bf7b46",
    )

    def __init__(self, environment_url: str, profile_hint: Optional[str] = None) -> None:
        self._environment_url = environment_url.rstrip("/")
        self._profile_hint = profile_hint

    def acquire_token(self) -> PacCliToken:
        """Return a PAC CLI access token or raise an informative error."""

        cache = self._load_token_cache()
        profile = self._select_profile()
        client_id = self._discover_client_id(cache, profile)
        authority = self._build_authority(profile)
        persistence_scopes = self._build_scopes(profile)

        app = msal.PublicClientApplication(
            client_id=client_id,
            authority=authority,
            token_cache=cache,
        )

        account = self._select_account(app, profile)
        if not account:
            raise PacCliAuthError("PAC CLI token cache is missing a matching account")

        token_result = app.acquire_token_silent(persistence_scopes, account=account)
        if not token_result:
            token_result = app.acquire_token_silent(
                persistence_scopes,
                account=account,
                force_refresh=True,
            )

        if not token_result or "access_token" not in token_result:
            raise PacCliAuthError(
                "Acquire_token_silent returned no access token; run 'pac auth create' again"
            )

        try:
            expires_on = datetime.fromtimestamp(int(token_result["expires_on"]), tz=timezone.utc)
        except (KeyError, TypeError, ValueError) as exc:
            raise PacCliAuthError("PAC CLI token response missing expiry metadata") from exc

        cache.persist_if_changed()
        return PacCliToken(
            access_token=token_result["access_token"],
            expires_on=expires_on,
            username=(profile.get("User") or account.get("username") or ""),
            environment_url=self._environment_url,
        )

    # ---------------------------------------------------------------------
    # Internal helpers
    # ---------------------------------------------------------------------
    def _load_token_cache(self) -> PersistedTokenCache:
        if PersistedTokenCache is None:
            raise PacCliNotConfiguredError("msal-extensions is not installed")

        directory = self._find_profile_directory()
        cache_path = directory / "tokencache_msalv3.dat"
        if not cache_path.exists():
            raise PacCliNotConfiguredError(
                "PAC CLI token cache not found; run 'pac auth create' first"
            )

        persistence_factory = FilePersistenceWithDataProtection or FilePersistence
        if persistence_factory is None:
            raise PacCliNotConfiguredError("msal-extensions persistence helpers unavailable")

        persistence = persistence_factory(str(cache_path))
        cache = PersistedTokenCache(persistence)
        cache._reload_if_necessary()  # type: ignore[attr-defined]
        return cache

    def _select_profile(self) -> Dict[str, str]:
        directory = self._find_profile_directory()
        profile_path = directory / "authprofiles_v2.json"
        if not profile_path.exists():
            raise PacCliNotConfiguredError(
                "PAC CLI profile metadata missing; run 'pac auth create' first"
            )

        data = json.loads(profile_path.read_text())
        profiles = data.get("Profiles", [])
        if not profiles:
            raise PacCliNotConfiguredError("No PAC CLI authentication profiles defined")

        # Prefer explicit hints first.
        if self._profile_hint:
            for profile in profiles:
                if self._matches_hint(profile):
                    return profile

        # Next, pick the profile matching the requested environment URL.
        environment = self._environment_url.lower()
        for profile in profiles:
            resource = (profile.get("Resource") or "").rstrip("/").lower()
            if resource and resource == environment:
                return profile

        # Fall back to the currently selected profile.
        current = data.get("Current", {})
        for value in current.values():
            if isinstance(value, dict):
                if not self._profile_hint or self._matches_hint(value):
                    return value

        # Finally return the first profile.
        return profiles[0]

    def _matches_hint(self, profile: Dict[str, str]) -> bool:
        hint = (self._profile_hint or "").lower()
        if not hint:
            return False
        for key in ("FriendlyName", "Name", "EnvironmentId", "Resource", "User"):
            value = profile.get(key)
            if value and hint in value.lower():
                return True
        return False

    def _discover_client_id(self, cache: PersistedTokenCache, profile: Dict[str, str]) -> str:
        cache_entries = cache._cache.get("AccessToken", {})  # type: ignore[attr-defined]
        if cache_entries:
            target_fragment = profile.get("Resource") or self._environment_url
            target_fragment = target_fragment.rstrip("/").lower()
            for entry in cache_entries.values():
                target = entry.get("target", "")
                if target_fragment and target_fragment in target.replace("//", "/").lower():
                    client_id = entry.get("client_id")
                    if client_id:
                        return client_id

        return self._CLIENT_ID_FALLBACKS[0]

    def _build_authority(self, profile: Dict[str, str]) -> str:
        tenant_id = profile.get("TenantId")
        if tenant_id:
            return f"https://login.windows.net/{tenant_id}"
        authority = profile.get("Authority")
        if authority:
            return authority
        return "https://login.microsoftonline.com/organizations"

    def _build_scopes(self, profile: Dict[str, str]) -> Iterable[str]:
        resource = (profile.get("Resource") or self._environment_url).rstrip("/")
        return [f"{resource}/.default"]

    def _select_account(
        self, app: msal.PublicClientApplication, profile: Dict[str, str]
    ) -> Optional[Dict[str, str]]:
        username = (profile.get("User") or "").lower()
        tenant_id = (profile.get("TenantId") or "").lower()
        accounts = app.get_accounts()
        if username:
            for account in accounts:
                if account.get("username", "").lower() == username:
                    return account
        if tenant_id:
            for account in accounts:
                if account.get("realm", "").lower() == tenant_id:
                    return account
        return accounts[0] if accounts else None

    def _find_profile_directory(self) -> Path:
        for candidate in self._candidate_directories():
            if candidate.exists():
                return candidate
        raise PacCliNotConfiguredError("PAC CLI configuration directory not found")

    def _candidate_directories(self) -> Iterable[Path]:
        candidates = []
        local_appdata = os.getenv("LOCALAPPDATA")
        if local_appdata:
            candidates.append(Path(local_appdata) / "Microsoft" / "PowerAppsCli")
        home = Path.home()
        candidates.append(home / ".local" / "share" / "Microsoft" / "PowerAppsCli")
        candidates.append(home / "AppData" / "Local" / "Microsoft" / "PowerAppsCli")
        candidates.append(home / ".PowerAppsCli")
        seen = set()
        unique_candidates = []
        for candidate in candidates:
            key = str(candidate)
            if key not in seen:
                seen.add(key)
                unique_candidates.append(candidate)
        return unique_candidates


def try_acquire_pac_cli_token(
    environment_url: str,
    profile_hint: Optional[str] = None,
) -> Optional[PacCliToken]:
    """
    Attempt to reuse PAC CLI authentication for the specified environment.

    Returns a :class:`PacCliToken` on success or ``None`` if PAC CLI credentials
    are unavailable. Errors are logged for troubleshooting but swallowed so that
    callers can fall back to alternate authentication flows.
    """

    provider = PacCliTokenProvider(environment_url=environment_url, profile_hint=profile_hint)
    try:
        token = provider.acquire_token()
        logger.debug(
            "Using PAC CLI token for Dataverse environment %s (user=%s)",
            token.environment_url,
            token.username,
        )
        return token
    except PacCliNotConfiguredError as exc:
        logger.debug("PAC CLI authentication not available: %s", exc)
    except PacCliAuthError as exc:
        logger.warning("PAC CLI authentication failed: %s", exc)
    except Exception as exc:  # pragma: no cover - defensive safeguard
        logger.exception("Unexpected PAC CLI authentication failure: %s", exc)
    return None
