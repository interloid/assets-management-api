from enum import StrEnum


class UserRole(StrEnum):
    ADMIN = "admin"
    USER = "user"


class AssetType(StrEnum):
    LAPTOP = "laptop"
    MONITOR = "monitor"
    PHONE = "phone"
    ACCESSORY = "accessory"


class AssetStatus(StrEnum):
    IN_STOCK = "in_stock"
    ASSIGNED = "assigned"
    REPAIR = "repair"
    RETIRED = "retired"


class WarrantyExpiry(StrEnum):
    EXPIRES_IN_30_DAYS = ("expires_in_30_days",)
    EXPIRES_IN_90_DAYS = "expires_in_90_days"
    ALREADY_EXPIRED = "already_expired"


class FileType(StrEnum):
    PDF = "application/pdf"
    JPEG = "image/jpeg"
    PNG = "image/png"
    WEBP = "image/webp"


class FileUploadStatus(StrEnum):
    PENDING = "pending"
    UPLOADED = "uploaded"
    FAILED = "failed"
    DELETED = "deleted"
