from fastapi import APIRouter

from app.api.v1.endpoints import asset_files, assets, auth, csv_export, internal, users

router = APIRouter(
    prefix="/api/v1",
)
router.include_router(auth.router)
router.include_router(users.router)
router.include_router(assets.router)
router.include_router(csv_export.router)
router.include_router(asset_files.router)
router.include_router(internal.router)
