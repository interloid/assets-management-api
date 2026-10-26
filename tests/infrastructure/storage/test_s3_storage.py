from urllib.parse import parse_qs, urlparse

import boto3
import pytest
from botocore.config import Config
from botocore.exceptions import ClientError
from moto import mock_aws

from app.infrastructure.storage.s3_storage import S3Storage

BUCKET_NAME = "test-assets-management-files"
REGION = "us-east-1"


@pytest.fixture
def s3_storage():
    """Create an isolated, mocked S3 bucket for each test."""
    with mock_aws():
        client = boto3.client(
            "s3",
            region_name=REGION,
            aws_access_key_id="testing",
            aws_secret_access_key="testing",
            config=Config(signature_version="s3v4"),
        )
        client.create_bucket(Bucket=BUCKET_NAME)

        storage = S3Storage(
            client=client,
            presign_client=client,
            bucket_name=BUCKET_NAME,
        )
        yield storage


def test_generate_presigned_put_url(s3_storage):
    object_key = "assets/test-asset/file.pdf"
    content_type = "application/pdf"

    url = s3_storage.generate_presigned_put_url(
        object_key=object_key,
        content_type=content_type,
    )

    parsed_url = urlparse(url)
    query = parse_qs(parsed_url.query)

    assert parsed_url.scheme == "https"
    assert parsed_url.netloc.startswith(f"{BUCKET_NAME}.")
    assert parsed_url.path.endswith(object_key)
    assert query["X-Amz-Expires"] == [str(S3Storage.PUT_URL_EXPIRY_SECONDS)]
    assert "X-Amz-Signature" in query


def test_generate_presigned_get_url(s3_storage):
    object_key = "assets/test-asset/file.pdf"

    url = s3_storage.generate_presigned_get_url(object_key)

    parsed_url = urlparse(url)
    query = parse_qs(parsed_url.query)

    assert parsed_url.scheme == "https"
    assert parsed_url.netloc.startswith(f"{BUCKET_NAME}.")
    assert parsed_url.path.endswith(object_key)
    assert query["X-Amz-Expires"] == [str(S3Storage.GET_URL_EXPIRY_SECONDS)]
    assert "X-Amz-Signature" in query


def test_get_object_metadata_returns_metadata_for_existing_object(
    s3_storage,
):
    object_key = "assets/test-asset/file.pdf"
    content = b"test PDF content"

    s3_storage.client.put_object(
        Bucket=BUCKET_NAME,
        Key=object_key,
        Body=content,
        ContentType="application/pdf",
        Metadata={"source": "pytest"},
    )

    metadata = s3_storage.get_object_metadata(object_key)

    assert metadata is not None
    assert metadata["content_type"] == "application/pdf"
    assert metadata["content_length"] == len(content)
    assert metadata["etag"]
    assert metadata["last_modified"] is not None
    assert metadata["metadata"] == {"source": "pytest"}


def test_get_object_metadata_returns_none_for_missing_object(
    s3_storage,
):
    metadata = s3_storage.get_object_metadata("assets/missing/file.pdf")

    assert metadata is None


def test_get_object_metadata_reraises_unexpected_s3_error(
    s3_storage,
    monkeypatch,
):
    def raise_access_denied(**kwargs):
        raise ClientError(
            {
                "Error": {
                    "Code": "AccessDenied",
                    "Message": "Access denied",
                },
                "ResponseMetadata": {"HTTPStatusCode": 403},
            },
            "HeadObject",
        )

    monkeypatch.setattr(
        s3_storage.client,
        "head_object",
        raise_access_denied,
    )

    with pytest.raises(ClientError) as exc_info:
        s3_storage.get_object_metadata("assets/test/file.pdf")

    assert exc_info.value.response["Error"]["Code"] == "AccessDenied"


def test_delete_object_removes_existing_object(s3_storage):
    object_key = "assets/test-asset/file.pdf"

    s3_storage.client.put_object(
        Bucket=BUCKET_NAME,
        Key=object_key,
        Body=b"test content",
    )

    s3_storage.delete_object(object_key)

    assert s3_storage.get_object_metadata(object_key) is None


def test_delete_object_is_idempotent_for_missing_object(s3_storage):
    object_key = "assets/test-asset/missing.pdf"

    s3_storage.delete_object(object_key)

    assert s3_storage.get_object_metadata(object_key) is None
