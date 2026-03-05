"""Auto-profiling engine — analyzes payloads and suggests pruning profiles."""

import re
from dataclasses import dataclass, field

# Patterns that indicate sensitive data → should be masked
SENSITIVE_PATTERNS: list[re.Pattern] = [
    re.compile(p, re.IGNORECASE)
    for p in [
        r"ssn",
        r"social.?security",
        r"tax.?id",
        r"password",
        r"passwd",
        r"secret",
        r"token",
        r"api.?key",
        r"access.?key",
        r"credit.?card",
        r"card.?number",
        r"cvv",
        r"routing.?number",
        r"account.?number",
        r"private.?key",
        r"auth",
        r"bearer",
        r"session.?id",
        r"cookie",
    ]
]

# Patterns that indicate system metadata → should be stripped
NOISE_PATTERNS: list[re.Pattern] = [
    re.compile(p, re.IGNORECASE)
    for p in [
        r"^id$",
        r".*_id$",
        r".*Id$",
        r"attributes",
        r"modstamp",
        r"modified.?by",
        r"created.?by",
        r"owned.?by",
        r"owner.?id",
        r"is.?deleted",
        r"system.?mod",
        r"last.?modified",
        r"last.?viewed",
        r"last.?referenced",
        r"photo.?url",
        r"master.?record",
        r"record.?type",
        r"jigsaw",
        r"clean.?status",
        r"duns",
        r"sic",
        r"naics",
        r"__c$",
        r".*_url$",
        r".*_uri$",
        r".*_link$",
    ]
]


@dataclass
class ProfileSuggestion:
    """Result of auto-profiling a sample payload."""

    profile_name: str
    keep: list[str] = field(default_factory=list)
    mask: list[str] = field(default_factory=list)
    strip: list[str] = field(default_factory=list)
    mask_pattern: str = "***REDACTED***"
    confidence: float = 0.0

    def to_yaml_dict(self) -> dict:
        """Return a dict ready to be serialized to YAML."""
        result: dict = {"keep": self.keep}
        if self.mask:
            result["mask"] = self.mask
            result["mask_pattern"] = self.mask_pattern
        return result


def _classify_field(name: str) -> str:
    """Classify a field as 'keep', 'mask', or 'strip'."""
    for pattern in SENSITIVE_PATTERNS:
        if pattern.search(name):
            return "mask"
    for pattern in NOISE_PATTERNS:
        if pattern.search(name):
            return "strip"
    return "keep"


def _flatten_keys(payload: dict, prefix: str = "") -> list[str]:
    """Recursively extract all field names from a nested payload."""
    keys = []
    for key, value in payload.items():
        keys.append(key)
        if isinstance(value, dict):
            keys.extend(_flatten_keys(value))
        elif isinstance(value, list) and value and isinstance(value[0], dict):
            keys.extend(_flatten_keys(value[0]))
    return list(dict.fromkeys(keys))  # deduplicate, preserve order


def suggest_profile(
    payload: dict,
    profile_name: str = "auto_generated",
) -> ProfileSuggestion:
    """Analyze a sample payload and suggest a pruning profile.

    Classifies each field as keep, mask, or strip based on
    field name pattern matching against known sensitive and
    system metadata patterns.
    """
    all_keys = _flatten_keys(payload)
    suggestion = ProfileSuggestion(profile_name=profile_name)

    for key in all_keys:
        category = _classify_field(key)
        if category == "mask":
            suggestion.mask.append(key)
            suggestion.keep.append(key)  # masked fields are also kept
        elif category == "strip":
            suggestion.strip.append(key)
        else:
            suggestion.keep.append(key)

    total = len(all_keys)
    if total > 0:
        classified = len(suggestion.mask) + len(suggestion.strip)
        suggestion.confidence = round(classified / total, 2)

    return suggestion
