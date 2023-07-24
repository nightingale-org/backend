from __future__ import annotations

import time

import aioboto3

from fastapi import UploadFile

from src.config import app_config


# TODO implement pre-signed url upload when public_url is False
async def upload_file(
    boto3_session: aioboto3.Session,
    file: UploadFile,
    *,
    return_public_url: bool,
    cache_file: bool = True,
    file_name_prefix: str | None = None,
) -> str:
    file_descriptor = file.file
    extra_args = {
        "ContentType": file.content_type,
    }
    file_name = file.filename

    if file_name_prefix:
        file_name = f"{file_name_prefix}-{file_name}"

    if not cache_file:
        extra_args["CacheControl"] = "max-age=0, must-revalidate"

    async with boto3_session.client("s3") as s3:
        await file.seek(0)
        await s3.upload_fileobj(
            file_descriptor,
            app_config.s3_bucket_name,
            file_name,
            ExtraArgs=extra_args,
        )

    return f"https://{app_config.s3_bucket_name}.s3.amazonaws.com/{file_name}?timestamp={int(time.time())}"
