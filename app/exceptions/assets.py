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
