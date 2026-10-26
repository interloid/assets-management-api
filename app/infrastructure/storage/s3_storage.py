from typing import Any

from botocore.exceptions import ClientError

from app.core.config import settings
from app.infrastructure.storage.s3 import s3_client, s3_presign_client


class S3Storage:
    PUT_URL_EXPIRY_SECONDS = 300
    GET_URL_EXPIRY_SECONDS = 900

    def __init__(
        self,
        client: Any | None = None,
        bucket_name: str | None = None,
        presign_client: Any | None = None,
    ) -> None:
        self.client = client if client is not None else s3_client
        self.presign_client = (
            presign_client
            if presign_client is not None
            else (client if client is not None else s3_presign_client)
        )
        self.bucket_name = (
            bucket_name if bucket_name is not None else settings.S3_BUCKET_NAME
        )

    def generate_presigned_put_url(
        self,
        object_key: str,
        content_type: str,
    ) -> str:
        return self.presign_client.generate_presigned_url(
            ClientMethod="put_object",
            Params={
                "Bucket": self.bucket_name,
                "Key": object_key,
                "ContentType": content_type,
            },
            ExpiresIn=self.PUT_URL_EXPIRY_SECONDS,
            HttpMethod="PUT",
        )

    def generate_presigned_get_url(self, object_key: str) -> str:
        return self.presign_client.generate_presigned_url(
            ClientMethod="get_object",
            Params={
                "Bucket": self.bucket_name,
                "Key": object_key,
            },
            ExpiresIn=self.GET_URL_EXPIRY_SECONDS,
            HttpMethod="GET",
        )

    def get_object_metadata(self, object_key: str) -> dict | None:
        try:
            response = self.client.head_object(
                Bucket=self.bucket_name,
                Key=object_key,
            )
        except ClientError as exc:
            error_code = exc.response.get("Error", {}).get("Code", "")
            status_code = exc.response.get("ResponseMetadata", {}).get("HTTPStatusCode")

            if error_code in {"404", "NoSuchKey", "NotFound"} or status_code == 404:
                return None

            raise

        return {
            "content_type": response.get("ContentType"),
            "content_length": response.get("ContentLength"),
            "etag": response.get("ETag"),
            "last_modified": response.get("LastModified"),
            "metadata": response.get("Metadata", {}),
        }

    def delete_object(self, object_key: str) -> None:
        self.client.delete_object(
            Bucket=self.bucket_name,
            Key=object_key,
        )
