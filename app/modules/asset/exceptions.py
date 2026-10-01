from app.core.exceptions import AppError


class AssetAlreadyExistsError(AppError):
    status_code = 409
    code = "ASSET_ALREADY_EXISTS"
    message = "An asset with the provided details already exists"


class AssetTagAlreadyExistsError(AssetAlreadyExistsError):
    code = "ASSET_TAG_ALREADY_EXISTS"
    message = "An asset with this asset tag already exists"


class SerialNumberAlreadyExistsError(AssetAlreadyExistsError):
    code = "SERIAL_NUMBER_ALREADY_EXISTS"
    message = "An asset with this serial number already exists"


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
        self.message = (
            f"Asset status cannot be changed from '{current_status}' to '{new_status}'"
        )
        super().__init__()


class AssetDeleteConflictError(AppError):
    status_code = 409
    code = "ASSET_DELETE_CONFLICT"
    message = "Asset can only be deleted when its status is 'in_stock' or 'retired'"


class AssetAssignmentUserNotFoundError(AppError):
    status_code = 404
    code = "ASSET_ASSIGNMENT_USER_NOT_FOUND"
    message = "The user assigned to this asset was not found"


class AssetAssignmentUserInactiveError(AppError):
    status_code = 409
    code = "ASSET_ASSIGNMENT_USER_INACTIVE"
    message = "The user assigned to this asset is inactive"
