"""ORM model for the audit log table.

Design: never store the raw payload (data minimization / zero-retention).
Only metadata about the transaction is persisted for compliance evidence.
"""

from datetime import UTC, datetime

from sqlalchemy import DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from .database import Base


class PruneAuditLog(Base):
    """Records every pruning transaction for compliance and observability."""

    __tablename__ = "prune_audit_log"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    source_profile: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    original_payload_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    pruned_payload_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    tokens_saved_estimate: Mapped[int] = mapped_column(Integer, nullable=False)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )
