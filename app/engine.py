"""YAML-driven pruning engine — the core of ContextGate.

The engine has zero knowledge of any specific data source. It reads its
behavior entirely from profiles.yaml at runtime. To support a new source,
add a YAML block — no Python changes required. (Open/Closed Principle)
"""

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from .config import get_settings

DEFAULT_MASK_PATTERN = "***REDACTED***"
BYTES_PER_TOKEN = 4


@dataclass
class PruneResult:
    """Output of a single pruning operation."""

    pruned_payload: dict[str, Any]
    original_bytes: int
    pruned_bytes: int
    bytes_saved: int
    tokens_saved_estimate: int


class ProfileNotFoundError(Exception):
    """Raised when a requested profile name does not exist in profiles.yaml."""


class PruneEngine:
    """Config-driven pruning engine.

    One instance is created at app startup and reused across all requests.
    Each YAML profile acts as a Strategy defining keep/mask behavior.
    """

    def __init__(self, profiles_path: str | None = None) -> None:
        """Load and parse profiles.yaml."""
        resolved = profiles_path or get_settings().profiles_path
        path = Path(resolved)

        if not path.exists():
            raise FileNotFoundError(
                f"Profiles file not found: '{path.resolve()}'. "
                "Ensure profiles.yaml exists or set PROFILES_PATH."
            )

        with path.open("r") as f:
            self._profiles: dict[str, dict] = yaml.safe_load(f) or {}

    def list_profiles(self) -> list[str]:
        """Return all registered profile names."""
        return list(self._profiles.keys())

    def prune(self, raw: dict[str, Any], profile_name: str) -> PruneResult:
        """Prune a raw payload according to the named profile."""
        profile = self._get_profile(profile_name)
        keep_fields = self._normalize_set(profile.get("keep", []))
        mask_fields = self._normalize_set(profile.get("mask", []))
        mask_pattern = profile.get("mask_pattern", DEFAULT_MASK_PATTERN)

        pruned = self._apply_rules(raw, keep_fields, mask_fields, mask_pattern)

        original_bytes = len(json.dumps(raw, default=str).encode())
        pruned_bytes = len(json.dumps(pruned, default=str).encode())
        bytes_saved = max(0, original_bytes - pruned_bytes)

        return PruneResult(
            pruned_payload=pruned,
            original_bytes=original_bytes,
            pruned_bytes=pruned_bytes,
            bytes_saved=bytes_saved,
            tokens_saved_estimate=bytes_saved // BYTES_PER_TOKEN,
        )

    def prune_batch(
        self, raw_list: list[dict[str, Any]], profile_name: str
    ) -> tuple[list[dict[str, Any]], PruneResult]:
        """Prune a list of payloads and return aggregate metrics."""
        pruned_list: list[dict[str, Any]] = []
        total_original = 0
        total_pruned = 0

        for item in raw_list:
            result = self.prune(item, profile_name)
            pruned_list.append(result.pruned_payload)
            total_original += result.original_bytes
            total_pruned += result.pruned_bytes

        bytes_saved = max(0, total_original - total_pruned)
        aggregate = PruneResult(
            pruned_payload={},
            original_bytes=total_original,
            pruned_bytes=total_pruned,
            bytes_saved=bytes_saved,
            tokens_saved_estimate=bytes_saved // BYTES_PER_TOKEN,
        )
        return pruned_list, aggregate

    def _get_profile(self, profile_name: str) -> dict:
        """Retrieve a profile by name or raise ProfileNotFoundError."""
        if profile_name not in self._profiles:
            available = ", ".join(self._profiles.keys())
            raise ProfileNotFoundError(
                f"Profile '{profile_name}' not found. Available: {available}"
            )
        return self._profiles[profile_name]

    def _apply_rules(
        self,
        data: dict[str, Any],
        keep_fields: set[str],
        mask_fields: set[str],
        mask_pattern: str,
    ) -> dict[str, Any]:
        """Apply keep/mask rules, recursing into nested dicts and lists."""
        result: dict[str, Any] = {}
        for key, value in data.items():
            normalized = key.lower()

            if normalized in mask_fields:
                result[key] = mask_pattern
            elif normalized in keep_fields:
                result[key] = self._prune_value(value, keep_fields, mask_fields, mask_pattern)

        return result

    def _prune_value(
        self,
        value: Any,
        keep_fields: set[str],
        mask_fields: set[str],
        mask_pattern: str,
    ) -> Any:
        """Recursively prune nested dicts and lists."""
        if isinstance(value, dict):
            return self._apply_rules(value, keep_fields, mask_fields, mask_pattern)
        if isinstance(value, list):
            return [
                self._prune_value(item, keep_fields, mask_fields, mask_pattern) for item in value
            ]
        return value

    @staticmethod
    def _normalize_set(fields: list[str]) -> set[str]:
        """Lowercase all field names for case-insensitive matching."""
        return {f.lower() for f in fields}
