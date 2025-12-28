from minio import Minio
from minio.error import S3Error
from app.core.config import settings
import io
import logging

logger = logging.getLogger(__name__)

class StorageService:
    def __init__(self):
        self.client = Minio(
            settings.MINIO_ENDPOINT,
            access_key=settings.MINIO_ACCESS_KEY,
            secret_key=settings.MINIO_SECRET_KEY,
            secure=settings.MINIO_SECURE
        )
        self.bucket_name = settings.MINIO_BUCKET_NAME
        self.ensure_bucket_exists()

    def ensure_bucket_exists(self):
        try:
            if not self.client.bucket_exists(self.bucket_name):
                self.client.make_bucket(self.bucket_name)
                logger.info(f"Bucket '{self.bucket_name}' created.")
        except S3Error as e:
            logger.error(f"Error checking/creating bucket: {e}")
            raise

    def upload_file(self, file_data: bytes, object_name: str, content_type: str = "application/octet-stream"):
        """
        Uploads a file to MinIO.
        """
        try:
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
            self.client.remove_object(self.bucket_name, object_name)
        except S3Error as e:
            logger.error(f"Error deleting file: {e}")
            raise

storage_service = StorageService()
