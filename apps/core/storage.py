import uuid

from django.conf import settings
from django.core.files.storage import default_storage

def max_direct_upload_bytes():
    return settings.MAX_DIRECT_UPLOAD_MB * 1024 * 1024


def r2_media_storage():
    """Storage for Lesson.video_file/document_file — Cloudflare R2 when configured,
    otherwise falls back to the local default storage (dev machines without R2 set up)."""
    if not settings.USE_R2_STORAGE:
        return default_storage

    from storages.backends.s3 import S3Storage

    return S3Storage()


def generate_presigned_upload(*, filename, content_type, folder):
    """Presigned PUT URL so the browser uploads a lesson's video/document straight to
    R2 — the bytes never transit the Django server, sidestepping nginx/Cloudflare body
    size limits entirely for large course videos."""
    import boto3
    from botocore.client import Config as BotoConfig

    client = boto3.client(
        's3',
        endpoint_url=settings.AWS_S3_ENDPOINT_URL,
        aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
        region_name=settings.AWS_S3_REGION_NAME,
        config=BotoConfig(signature_version=settings.AWS_S3_SIGNATURE_VERSION),
    )
    ext = filename.rsplit('.', 1)[-1] if '.' in filename else 'bin'
    key = f'{folder}/{uuid.uuid4().hex}.{ext}'
    upload_url = client.generate_presigned_url(
        'put_object',
        Params={'Bucket': settings.AWS_STORAGE_BUCKET_NAME, 'Key': key, 'ContentType': content_type},
        ExpiresIn=900,
    )
    return {'upload_url': upload_url, 'key': key, 'content_type': content_type}


def is_r2_backed(file_field):
    """True when this FieldFile lives on R2 rather than local disk (scorm_package and
    LessonResource.file were deliberately left on local storage — see the R2 migration)."""
    if not file_field or not settings.USE_R2_STORAGE:
        return False
    from storages.backends.s3 import S3Storage

    return isinstance(file_field.storage, S3Storage)


def generate_presigned_download(key, *, download_filename=None, expires_in=3600):
    """Presigned GET straight to R2 — used to redirect playback/download requests
    instead of Django buffering the whole object into memory first (django-storages'
    S3 file wrapper downloads the entire object on open(), which made every seek in a
    500MB video re-fetch the whole file through the VPS before serving a byte range)."""
    import boto3
    from botocore.client import Config as BotoConfig

    client = boto3.client(
        's3',
        endpoint_url=settings.AWS_S3_ENDPOINT_URL,
        aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
        region_name=settings.AWS_S3_REGION_NAME,
        config=BotoConfig(signature_version=settings.AWS_S3_SIGNATURE_VERSION),
    )
    params = {'Bucket': settings.AWS_STORAGE_BUCKET_NAME, 'Key': key}
    if download_filename:
        params['ResponseContentDisposition'] = f'attachment; filename="{download_filename}"'
    return client.generate_presigned_url('get_object', Params=params, ExpiresIn=expires_in)
