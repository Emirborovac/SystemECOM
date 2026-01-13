import os
import uuid
from functools import lru_cache

import boto3
from botocore.config import Config

from app.core.config import settings


def _ensure_local_storage_dir() -> str:
    base = settings.file_storage_root
    if not os.path.isabs(base):
        base = os.path.join(os.getcwd(), base)
    os.makedirs(base, exist_ok=True)
    return base


@lru_cache(maxsize=1)
def _s3_client():
    if settings.s3_endpoint_url is None:
        raise RuntimeError("S3_ENDPOINT_URL required for S3/MINIO storage")
    if settings.s3_access_key_id is None or settings.s3_secret_access_key is None:
        raise RuntimeError("S3_ACCESS_KEY_ID and S3_SECRET_ACCESS_KEY required for S3/MINIO storage")
    return boto3.client(
        "s3",
        endpoint_url=settings.s3_endpoint_url,
        region_name=settings.s3_region,
        aws_access_key_id=settings.s3_access_key_id,
        aws_secret_access_key=settings.s3_secret_access_key,
        config=Config(s3={"addressing_style": "path"}),
    )


def save_bytes(*, data: bytes, filename: str) -> tuple[str, int]:
    """
    Returns: (storage_key, size_bytes).
    The active provider is determined by settings.file_storage_provider.
    """
    key = f"{uuid.uuid4().hex}_{filename}"
    provider = settings.file_storage_provider.upper()
    if provider == "LOCAL":
        base = _ensure_local_storage_dir()
        path = os.path.join(base, key)
        with open(path, "wb") as f:
            f.write(data)
        return key, len(data)

    bucket = settings.s3_bucket
    if not bucket:
        raise RuntimeError("S3_BUCKET required for S3/MINIO storage")

    client = _s3_client()
    client.put_object(Bucket=bucket, Key=key, Body=data)
    return key, len(data)


def load_bytes(*, storage_provider: str, storage_key: str) -> bytes:
    provider = (storage_provider or "LOCAL").upper()
    if provider == "LOCAL":
        base = _ensure_local_storage_dir()
        path = os.path.join(base, storage_key)
        with open(path, "rb") as f:
            return f.read()

    bucket = settings.s3_bucket
    if not bucket:
        raise RuntimeError("S3_BUCKET required for S3/MINIO storage")

    client = _s3_client()
    obj = client.get_object(Bucket=bucket, Key=storage_key)
    return obj["Body"].read()


