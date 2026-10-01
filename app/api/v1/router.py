from fastapi import APIRouter

from app.api.v1.endpoints import assets, auth, users

router = APIRouter(
    prefix="/api/v1",
)
router.include_router(auth.router)
router.include_router(users.router)
router.include_router(assets.router)
