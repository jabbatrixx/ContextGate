"""Audit log, stats, profile discovery, and auto-profiling endpoints."""

import yaml
from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db
from ..models import PruneAuditLog
from ..profiler import suggest_profile
from ..schemas import (
    AuditLogEntry,
    AuditStatsResponse,
    AutoProfileRequest,
    AutoProfileResponse,
    ProfileListResponse,
)

router = APIRouter(prefix="/api/v1", tags=["Audit & Discovery"])


def get_engine(request: Request):
    """Retrieve the shared PruneEngine from app state."""
    return request.app.state.engine


@router.get("/profiles", response_model=ProfileListResponse, summary="List available profiles")
async def list_profiles(engine=Depends(get_engine)) -> ProfileListResponse:
    """Return all profile names registered in profiles.yaml."""
    profiles = engine.list_profiles()
    return ProfileListResponse(profiles=profiles, count=len(profiles))


@router.get("/audit/logs", response_model=list[AuditLogEntry], summary="Retrieve audit log entries")
async def get_audit_logs(
    db: AsyncSession = Depends(get_db),
    limit: int = Query(default=50, ge=1, le=500, description="Max records to return"),
    offset: int = Query(default=0, ge=0, description="Pagination offset"),
    source_profile: str | None = Query(default=None, description="Filter by profile name"),
) -> list[AuditLogEntry]:
    """Paginated audit log with optional filter by source profile."""
    stmt = select(PruneAuditLog).order_by(PruneAuditLog.timestamp.desc())

    if source_profile:
        pattern = f"%{source_profile}%"
        stmt = stmt.where(PruneAuditLog.source_profile.ilike(pattern))

    stmt = stmt.offset(offset).limit(limit)
    result = await db.execute(stmt)
    rows = result.scalars().all()
    return [AuditLogEntry.model_validate(row) for row in rows]


@router.get(
    "/audit/stats",
    response_model=AuditStatsResponse,
    summary="Aggregate token savings statistics",
)
async def get_audit_stats(db: AsyncSession = Depends(get_db)) -> AuditStatsResponse:
    """Aggregate stats for compliance and cost dashboards."""
    stmt = select(
        func.count(PruneAuditLog.id).label("total_operations"),
        func.sum(PruneAuditLog.original_payload_bytes - PruneAuditLog.pruned_payload_bytes).label(
            "total_bytes_saved"
        ),
        func.sum(PruneAuditLog.tokens_saved_estimate).label("total_tokens_saved"),
    )
    result = await db.execute(stmt)
    row = result.one()
    return AuditStatsResponse(
        total_operations=row.total_operations or 0,
        total_bytes_saved=row.total_bytes_saved or 0,
        total_tokens_saved=row.total_tokens_saved or 0,
    )


@router.post(
    "/profile/suggest",
    response_model=AutoProfileResponse,
    summary="Auto-generate a pruning profile from a sample payload",
    tags=["Auto-Profiling"],
)
async def suggest(body: AutoProfileRequest) -> AutoProfileResponse:
    """Analyze a sample payload and suggest which fields to keep, mask, or strip."""
    suggestion = suggest_profile(body.payload, body.profile_name)
    yaml_preview = yaml.dump(
        {suggestion.profile_name: suggestion.to_yaml_dict()},
        default_flow_style=False,
        sort_keys=False,
    )
    return AutoProfileResponse(
        profile_name=suggestion.profile_name,
        keep=suggestion.keep,
        mask=suggestion.mask,
        strip=suggestion.strip,
        mask_pattern=suggestion.mask_pattern,
        confidence=suggestion.confidence,
        yaml_preview=yaml_preview,
    )
