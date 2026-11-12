from datetime import UTC, datetime, timedelta
from pathlib import Path
from urllib.parse import quote, urlencode

from botocore.signers import CloudFrontSigner
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa


class CloudFrontURLSigner:
    def __init__(
        self,
        *,
        domain: str,
        key_pair_id: str,
        private_key_path: str,
        expiry_seconds: int = 900,
    ) -> None:
        self.domain = domain.removeprefix("https://").rstrip("/")
        self.expiry_seconds = expiry_seconds

        private_key = serialization.load_pem_private_key(
            Path(private_key_path).read_bytes(),
            password=None,
        )

        if not isinstance(private_key, rsa.RSAPrivateKey):
            raise ValueError("CloudFront private key must be an RSA key")

        def rsa_signer(message: bytes) -> bytes:
            return private_key.sign(
                message,
                padding.PKCS1v15(),
                hashes.SHA1(),
            )

        self.signer = CloudFrontSigner(
            key_pair_id,
            rsa_signer,
        )

    def generate_signed_url(
        self,
        object_key: str,
        *,
        download: bool = False,
        filename: str | None = None,
    ) -> str:
        encoded_key = quote(object_key, safe="/")
        url = f"https://{self.domain}/{encoded_key}"

        if download:
            safe_filename = Path(filename or object_key).name
            safe_filename = (
                safe_filename.replace('"', "")
                .replace("\\", "")
                .replace("\r", "")
                .replace("\n", "")
            )
            disposition = f'attachment; filename="{safe_filename}"'
        else:
            disposition = "inline"

        query_string = urlencode(
            {
                "response-content-disposition": disposition,
            }
        )

        url = f"{url}?{query_string}"

        expires_at = datetime.now(UTC) + timedelta(seconds=self.expiry_seconds)

        return self.signer.generate_presigned_url(
            url,
            date_less_than=expires_at,
        )
