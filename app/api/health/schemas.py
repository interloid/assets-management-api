from typing import Literal

from pydantic import BaseModel


class ServiceStatus(BaseModel):
    status: Literal["ok", "down"]


class LivenessResponse(BaseModel):
    status: Literal["ok"]
    version: str


class HealthResponse(BaseModel):
    status: Literal["ok", "degraded"]
    services: dict[str, ServiceStatus]
