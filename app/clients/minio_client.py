import os
import boto3
from botocore.config import Config

MINIO_ENDPOINT = os.environ["MINIO_ENDPOINT"]
MINIO_PUBLIC_ENDPOINT = os.getenv("MINIO_PUBLIC_ENDPOINT", "http://localhost:9000")
MINIO_ACCESS_KEY = os.environ["MINIO_ACCESS_KEY"]
MINIO_SECRET_KEY = os.environ["MINIO_SECRET_KEY"]
BUCKET = os.environ["MINIO_BUCKET"]


def get_s3_client():
    """Internal client - talks to minio:9000 inside Docker network."""
    return boto3.client(
        "s3",
        endpoint_url=MINIO_ENDPOINT,
        aws_access_key_id=MINIO_ACCESS_KEY,
        aws_secret_access_key=MINIO_SECRET_KEY,
        config=Config(signature_version="s3v4")
    )


def get_public_s3_client():
    """Presigned URL client - uses localhost:9000 so URLs work from outside Docker."""
    return boto3.client(
        "s3",
        endpoint_url=MINIO_PUBLIC_ENDPOINT,
        aws_access_key_id=MINIO_ACCESS_KEY,
        aws_secret_access_key=MINIO_SECRET_KEY,
        config=Config(signature_version="s3v4")
    )


def upload_file(local_path: str, object_key: str) -> str:
    s3 = get_s3_client()
    s3.upload_file(local_path, BUCKET, object_key)
    return object_key


def download_file(object_key: str, local_path: str) -> str:
    s3 = get_s3_client()
    s3.download_file(BUCKET, object_key, local_path)
    return local_path


def presigned_upload_url(object_key: str, expiry: int = 600) -> str:
    s3 = get_public_s3_client()
    return s3.generate_presigned_url(
        "put_object",
        Params={"Bucket": BUCKET, "Key": object_key},
        ExpiresIn=expiry
    )


def presigned_download_url(object_key: str, expiry: int = 60) -> str:
    s3 = get_public_s3_client()
    return s3.generate_presigned_url(
        "get_object",
        Params={"Bucket": BUCKET, "Key": object_key},
        ExpiresIn=expiry
    )


def upload_exists(object_key: str) -> bool:
    try:
        s3 = get_s3_client()
        s3.head_object(Bucket=BUCKET, Key=object_key)
        return True
    except Exception:
        return False

def delete_object(object_key: str) -> None:
    s3 = get_s3_client()
    s3.delete_object(Bucket=BUCKET, Key=object_key)