from fastapi import APIRouter

router = APIRouter()


@router.get("/")
def home() -> dict[str, str]:
    return {"message": "This is Assets Management System"}
