from datetime import datetime
from uuid import UUID

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column
from uuid6 import uuid7

from app.shared.models.base import BaseModel


class BackgroundJob(BaseModel):
    __tablename__ = "background_jobs"

    job_type: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    idempotency_key: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), nullable=False, default=uuid7
    )

    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        server_default="pending",
    )

    task_id: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    last_error: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    __table_args__ = (
        UniqueConstraint(
            "job_type", "idempotency_key", name="uq_background_job_type_key"
        ),
        CheckConstraint(
            "status IN('pending', 'running', 'completed', 'failed')",
            name="ck_background_job_status",
        ),
    )
