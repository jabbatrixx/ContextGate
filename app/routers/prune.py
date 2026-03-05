"""Prune endpoints — single and batch payload processing."""

from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db
from ..engine import ProfileNotFoundError, PruneEngine, PruneResult
from ..models import PruneAuditLog
from ..schemas import PruneBatchRequest, PruneRequest, PruneResponse

router = APIRouter(prefix="/api/v1/prune", tags=["Prune"])


def get_engine(request: Request) -> PruneEngine:
    """Retrieve the shared PruneEngine from app state."""
    return request.app.state.engine


async def write_audit_log(db: AsyncSession, profile: str, result: PruneResult) -> None:
    """Persist a pruning audit entry (metadata only, never raw data)."""
    db.add(
        PruneAuditLog(
            source_profile=profile,
            original_payload_bytes=result.original_bytes,
            pruned_payload_bytes=result.pruned_bytes,
            tokens_saved_estimate=result.tokens_saved_estimate,
        )
    )
    await db.commit()


@router.post("", response_model=PruneResponse, summary="Prune a single payload")
async def prune_single(
    request: PruneRequest,
    db: AsyncSession = Depends(get_db),
    engine: PruneEngine = Depends(get_engine),
) -> PruneResponse:
    """Prune a single JSON payload using the specified profile."""
    try:
        result = engine.prune(raw=request.payload, profile_name=request.profile)
    except ProfileNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e

    await write_audit_log(db, request.profile, result)

    return PruneResponse(
        source=request.profile,
        pruned_payload=result.pruned_payload,
        original_bytes=result.original_bytes,
        pruned_bytes=result.pruned_bytes,
        bytes_saved=result.bytes_saved,
        tokens_saved_estimate=result.tokens_saved_estimate,
        timestamp=datetime.now(UTC),
    )


@router.post("/batch", response_model=PruneResponse, summary="Prune a batch of payloads")
async def prune_batch(
    request: PruneBatchRequest,
    db: AsyncSession = Depends(get_db),
    engine: PruneEngine = Depends(get_engine),
) -> PruneResponse:
    """Prune a batch of JSON payloads using the specified profile."""
    if not request.payloads:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="payloads list must not be empty.",
        )

    try:
        pruned_list, aggregate = engine.prune_batch(
            raw_list=request.payloads, profile_name=request.profile
        )
    except ProfileNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e

    await write_audit_log(db, f"{request.profile}[batch:{len(request.payloads)}]", aggregate)

    return PruneResponse(
        source=request.profile,
        pruned_payload=pruned_list,
        original_bytes=aggregate.original_bytes,
        pruned_bytes=aggregate.pruned_bytes,
        bytes_saved=aggregate.bytes_saved,
        tokens_saved_estimate=aggregate.tokens_saved_estimate,
        timestamp=datetime.now(UTC),
    )
