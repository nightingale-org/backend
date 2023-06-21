from __future__ import annotations

import aioboto3

from fastapi import UploadFile

from src.config import app_config


# TODO implement pre-signed url upload when public_url is False
async def upload_file(
    boto3_session: aioboto3.Session, file: UploadFile, *, return_public_url: bool
) -> str:
    file_descriptor = file.file

    async with boto3_session.client("s3") as s3:
        await file.seek(0)
        await s3.upload_fileobj(
            file_descriptor,
            app_config.s3_bucket_name,
            file.filename,
            ExtraArgs={"ContentType": file.content_type},
        )

    return f"https://{app_config.s3_bucket_name}.s3.amazonaws.com/{file.filename}"
