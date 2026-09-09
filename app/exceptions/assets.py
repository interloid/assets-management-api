from app.exceptions.base import AppError


class AssetAlreadyExistsError(AppError):
    status_code = 409
    code = "ASSET_ALREADY_EXISTS"
    message = "Asset already exists"


class AssetTagAlreadyExistsError(AssetAlreadyExistsError):
    code = "ASSET_TAG_ALREADY_EXISTS"
    message = "Asset tag already exists"


class SerialNumberAlreadyExistsError(AssetAlreadyExistsError):
    code = "SERIAL_NUMBER_ALREADY_EXISTS"
    message = "Serial number already exists"


class AssetNotFoundError(AppError):
    status_code = 404

    code = "ASSET_NOT_FOUND"

    message = "Asset not found"


class InvalidAssetStatusTransitionError(AppError):
    status_code = 409
    code = "INVALID_ASSET_STATUS_TRANSITION"

    def __init__(
        self,
        current_status: str,
        new_status: str,
    ) -> None:
        self.message = f"Cannot change status from '{current_status}' to '{new_status}'"
        super().__init__()
