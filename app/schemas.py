"""Pydantic V2 request/response models for the ContextGate API."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class PruneRequest(BaseModel):
    """Single pruning request."""

    profile: str = Field(
        ...,
        description="Profile name from profiles.yaml (e.g. 'salesforce_account')",
        examples=["salesforce_account"],
    )
    payload: dict[str, Any] = Field(
        ...,
        description="Raw JSON payload to prune",
    )


class PruneBatchRequest(BaseModel):
    """Batch pruning request — many records, one profile."""

    profile: str = Field(
        ...,
        description="Profile name from profiles.yaml",
        examples=["snowflake_sales_report"],
    )
    payloads: list[dict[str, Any]] = Field(
        ...,
        description="List of raw JSON payloads to prune",
    )


class PruneResponse(BaseModel):
    """Standard response envelope returned by all prune endpoints."""

    source: str
    pruned_payload: dict[str, Any] | list[dict[str, Any]]
    original_bytes: int
    pruned_bytes: int
    bytes_saved: int
    tokens_saved_estimate: int
    timestamp: datetime


class AuditLogEntry(BaseModel):
    """Serializable representation of a PruneAuditLog row."""

    id: int
    source_profile: str
    original_payload_bytes: int
    pruned_payload_bytes: int
    tokens_saved_estimate: int
    timestamp: datetime

    model_config = {"from_attributes": True}


class AuditStatsResponse(BaseModel):
    """Aggregate statistics across all pruning operations."""

    total_operations: int
    total_bytes_saved: int
    total_tokens_saved: int


class ProfileListResponse(BaseModel):
    """Response for GET /api/v1/profiles."""

    profiles: list[str]
    count: int
