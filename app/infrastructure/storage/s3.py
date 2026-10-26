import boto3
from botocore.config import Config

from app.core.config import settings


def create_s3_client(endpoint_url: str | None):
    return boto3.client(
        "s3",
        region_name=settings.AWS_REGION,
        endpoint_url=endpoint_url,
        aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
        config=Config(signature_version="s3v4"),
    )


# Used by the API for S3 operations inside Docker.
s3_client = create_s3_client(settings.S3_ENDPOINT_URL)

# Used to generate URLs accessible from your host machine.
s3_presign_client = create_s3_client(
    settings.S3_PRESIGNED_URL_ENDPOINT or settings.S3_ENDPOINT_URL
)
