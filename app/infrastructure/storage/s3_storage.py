from typing import Any

from botocore.exceptions import ClientError

from app.core.config import settings
from app.infrastructure.storage.cloud_front_signer import CloudFrontURLSigner
from app.infrastructure.storage.s3 import s3_client, s3_presign_client


class S3Storage:
    PUT_URL_EXPIRY_SECONDS = 300

    def __init__(
        self,
        client: Any | None = None,
        bucket_name: str | None = None,
        presign_client: Any | None = None,
        cloudfront_signer: CloudFrontURLSigner | None = None,
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

        self.GET_URL_EXPIRY_SECONDS = settings.CLOUDFRONT_URL_EXPIRY_SECONDS

        cloudfront_config = (
            settings.CLOUDFRONT_DOMAIN,
            settings.CLOUDFRONT_KEY_PAIR_ID,
            settings.CLOUDFRONT_PRIVATE_KEY_PATH,
        )

        if cloudfront_signer is not None:
            self.cloudfront_signer = cloudfront_signer
        elif all(cloudfront_config):
            self.cloudfront_signer = CloudFrontURLSigner(
                domain=settings.CLOUDFRONT_DOMAIN,
                key_pair_id=settings.CLOUDFRONT_KEY_PAIR_ID,
                private_key_path=settings.CLOUDFRONT_PRIVATE_KEY_PATH,
                expiry_seconds=self.GET_URL_EXPIRY_SECONDS,
            )
        else:
            self.cloudfront_signer = None

        if any(cloudfront_config) and not all(cloudfront_config):
            raise ValueError("CloudFront configuration is incomplete")

    def generate_presigned_put_url(
        self,
        object_key: str,
        content_type: str,
        checksum_sha256: str,
    ) -> str:
        return self.presign_client.generate_presigned_url(
            ClientMethod="put_object",
            Params={
                "Bucket": self.bucket_name,
                "Key": object_key,
                "ContentType": content_type,
                "ChecksumSHA256": checksum_sha256,
            },
            ExpiresIn=self.PUT_URL_EXPIRY_SECONDS,
            HttpMethod="PUT",
        )

    def generate_presigned_get_url(
        self,
        object_key: str,
        *,
        download: bool = False,
        filename: str | None = None,
    ) -> str:
        if self.cloudfront_signer is not None:
            return self.cloudfront_signer.generate_signed_url(
                object_key,
                download=download,
                filename=filename,
            )

        if settings.ENVIRONMENT == "production":
            raise RuntimeError("CloudFront must be configured in production")

        disposition = "inline"

        if download:
            safe_filename = filename or object_key.rsplit("/", 1)[-1]
            safe_filename = (
                safe_filename.replace('"', "").replace("\r", "").replace("\n", "")
            )
            disposition = f'attachment; filename="{safe_filename}"'

        return self.presign_client.generate_presigned_url(
            ClientMethod="get_object",
            Params={
                "Bucket": self.bucket_name,
                "Key": object_key,
                "ResponseContentDisposition": disposition,
            },
            ExpiresIn=self.GET_URL_EXPIRY_SECONDS,
            HttpMethod="GET",
        )

    def get_object_metadata(self, object_key: str) -> dict | None:
        try:
            response = self.client.head_object(
                Bucket=self.bucket_name,
                Key=object_key,
                ChecksumMode="ENABLED",
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
            "checksum_sha256": response.get("ChecksumSHA256"),
            "metadata": response.get("Metadata", {}),
        }

    def delete_object(self, object_key: str) -> None:
        self.client.delete_object(
            Bucket=self.bucket_name,
            Key=object_key,
        )
