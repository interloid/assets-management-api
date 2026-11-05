import asyncio
import logging
import os
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select, update

from app.infrastructure.celery.app import celery_app
from app.infrastructure.celery.idempotency import (
    claim_job,
    mark_failed,
)
from app.infrastructure.database import AsyncSessionLocal, engine
from app.modules.asset.csv_export.csv_export_config import EXPORT_DIR
from app.modules.asset.csv_export.csv_export_model import AssetExport
from app.modules.asset.csv_export.csv_export_writter import (
    asset_to_csv,
    parse_filters,
    write_csv_file,
)
from app.modules.asset.models import Asset  # noqa: F401
from app.modules.asset.repositories import AssetRepository
from app.shared.background_jobs.models import BackgroundJob  # noqa: F401

logger = logging.getLogger(__name__)

JOB_TYPE = "asset_csv_export"


async def finish_export(
    export_id: UUID,
    idempotency_key: UUID,
    task_id: str,
    file_path: str,
) -> bool:
    async with AsyncSessionLocal() as session:
        async with session.begin():
            result = await session.execute(
                update(BackgroundJob)
                .where(
                    BackgroundJob.job_type == JOB_TYPE,
                    BackgroundJob.idempotency_key == idempotency_key,
                    BackgroundJob.task_id == task_id,
                    BackgroundJob.status == "running",
                )
                .values(
                    status="completed",
                    completed_at=datetime.now(UTC),
                    last_error=None,
                )
                .returning(BackgroundJob.id)
            )

            if result.scalar_one_or_none() is None:
                return False

            result = await session.execute(
                update(AssetExport)
                .where(
                    AssetExport.id == export_id,
                    AssetExport.status == "running",
                )
                .values(
                    status="completed",
                    file_path=file_path,
                )
                .returning(AssetExport.id)
            )

            if result.scalar_one_or_none() is None:
                raise RuntimeError(f"Could not complete export record {export_id}")
    return True


async def run_asset_export(
    *,
    export_id: UUID,
    task_id: str,
) -> dict:
    idempotency_key = export_id
    claimed = await claim_job(
        job_type=JOB_TYPE,
        idempotency_key=idempotency_key,
        task_id=task_id,
    )

    if not claimed:
        return {
            "status": "skipped",
            "export_id": str(export_id),
        }

    temporary_path = None

    try:
        async with AsyncSessionLocal() as session:
            async with session.begin():
                result = await session.execute(
                    select(AssetExport)
                    .where(
                        AssetExport.id == export_id,
                    )
                    .with_for_update()
                )
                export = result.scalar_one_or_none()

                if export is None:
                    raise ValueError(f"Export {export_id} was not found")

                export.status = "running"

                filters = parse_filters(export.filters)

        await asyncio.to_thread(
            EXPORT_DIR.mkdir,
            parents=True,
            exist_ok=True,
        )

        file_path = EXPORT_DIR / f"{export_id}-{task_id}.csv"

        temporary_path = EXPORT_DIR / f"{export_id}-{task_id}.tmp"

        async with AsyncSessionLocal() as session:
            repository = AssetRepository(session)
            async with session.begin():
                assets = await repository.list_for_export(**filters)

                rows = [asset_to_csv(asset) for asset in assets]

        assets_count = await asyncio.to_thread(
            write_csv_file,
            temporary_path,
            rows,
        )

        await asyncio.to_thread(os.replace, temporary_path, file_path)

        completed = await finish_export(
            export_id=export_id,
            idempotency_key=idempotency_key,
            task_id=task_id,
            file_path=str(file_path),
        )

        if not completed:
            await asyncio.to_thread(file_path.unlink, missing_ok=True)
            return {"status": "skipped", "export_id": str(export_id)}

        logger.info("CSV export completed: %s", export_id)

        return {
            "status": "completed",
            "export_id": str(export_id),
            "assets_count": assets_count,
        }

    except Exception as exc:
        try:
            failed = await mark_failed(
                job_type=JOB_TYPE,
                idempotency_key=idempotency_key,
                task_id=task_id,
                error=str(exc),
            )

            if failed:
                async with AsyncSessionLocal() as session:
                    async with session.begin():
                        await session.execute(
                            update(AssetExport)
                            .where(
                                AssetExport.id == export_id,
                                AssetExport.status != "completed",
                            )
                            .values(status="failed")
                        )

        except Exception:
            logger.exception(
                "Could not record export failure. export_id=%s",
                export_id,
            )

        if temporary_path is not None:
            try:
                await asyncio.to_thread(
                    temporary_path.unlink,
                    missing_ok=True,
                )
            except OSError:
                logger.exception(
                    "Could not remove temporary CSV file: %s",
                    temporary_path,
                )

        raise


async def run_export_with_cleanup(
    *,
    export_id: UUID,
    task_id: str,
) -> dict:
    try:
        return await run_asset_export(
            export_id=export_id,
            task_id=task_id,
        )
    finally:
        await engine.dispose()


@celery_app.task(
    bind=True,
    name="app.infrastructure.celery.csv_export_tasks.generate_asset_csv",
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_kwargs={"max_retries": 3},
)
def generate_asset_csv(
    self,
    export_id: str,
    request_id: str | None = None,
) -> dict:
    task_id = self.request.id

    log_context = {
        "request_id": request_id,
        "task_id": task_id,
        "export_id": export_id,
    }

    logger.info(
        "CSV export task started",
        extra=log_context,
    )

    try:
        result = asyncio.run(
            run_export_with_cleanup(
                export_id=UUID(export_id),
                task_id=task_id,
            )
        )

        logger.info(
            "CSV export task completed",
            extra=log_context,
        )

        return result

    except Exception:
        logger.exception(
            "CSV export task failed",
            extra=log_context,
        )
        raise
