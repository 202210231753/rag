import logging
import io
from typing import Optional

from app.core.config import settings

logger = logging.getLogger(__name__)


try:
    from minio import Minio  # type: ignore
    from minio.error import S3Error  # type: ignore
except Exception:  # pragma: no cover
    Minio = None  # type: ignore[assignment]
    S3Error = Exception  # type: ignore[assignment]


class StorageService:
    def __init__(self):
        if Minio is None:
            raise RuntimeError("未安装 minio 依赖，无法启用对象存储功能")

        self.client = Minio(
            settings.MINIO_ENDPOINT,
            access_key=settings.MINIO_ACCESS_KEY,
            secret_key=settings.MINIO_SECRET_KEY,
            secure=settings.MINIO_SECURE
        )
        self.bucket_name = settings.MINIO_BUCKET_NAME
        self._bucket_checked = False

    def ensure_bucket_exists(self):
        try:
            if not self.client.bucket_exists(self.bucket_name):
                self.client.make_bucket(self.bucket_name)
                logger.info(f"Bucket '{self.bucket_name}' created.")
            self._bucket_checked = True
        except S3Error as e:
            logger.error(f"Error checking/creating bucket: {e}")
            raise

    def upload_file(self, file_data: bytes, object_name: str, content_type: str = "application/octet-stream"):
        """
        Uploads a file to MinIO.
        """
        try:
            if not self._bucket_checked:
                self.ensure_bucket_exists()
            file_stream = io.BytesIO(file_data)
            self.client.put_object(
                self.bucket_name,
                object_name,
                file_stream,
                length=len(file_data),
                content_type=content_type
            )
            return object_name
        except S3Error as e:
            logger.error(f"Error uploading file: {e}")
            raise

    def get_file(self, object_name: str):
        """
        Gets a file stream from MinIO.
        """
        try:
            if not self._bucket_checked:
                self.ensure_bucket_exists()
            response = self.client.get_object(self.bucket_name, object_name)
            return response
        except S3Error as e:
            logger.error(f"Error getting file: {e}")
            raise

    def delete_file(self, object_name: str):
        """
        Deletes a file from MinIO.
        """
        try:
            if not self._bucket_checked:
                self.ensure_bucket_exists()
            self.client.remove_object(self.bucket_name, object_name)
        except S3Error as e:
            logger.error(f"Error deleting file: {e}")
            raise


_storage_service: Optional[StorageService] = None


def get_storage_service() -> StorageService:
    global _storage_service
    if _storage_service is None:
        _storage_service = StorageService()
    return _storage_service


storage_service = get_storage_service()
