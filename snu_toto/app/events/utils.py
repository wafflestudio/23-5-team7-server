from datetime import datetime
import json
import aioboto3
from fastapi import UploadFile
from snu_toto.app.common.exceptions import InvalidFormatException
from snu_toto.app.core.config import S3_SETTINGS
from snu_toto.app.core.date_utils import get_kst_now

def parse_event_data(data: str):
    """JSON 문자열을 EventCreateRequest 모델로 변환"""
    try:
        return json.loads(data)
    except json.JSONDecodeError:
        raise InvalidFormatException()

class S3Uploader:
    def __init__(self):
        self.bucket_name = S3_SETTINGS.S3_BUCKET_NAME
        self.region = S3_SETTINGS.S3_AWS_REGION

    async def upload_file(self, file: UploadFile, folder: str = "events") -> str:
        """파일을 S3에 업로드하고 URL을 반환"""
        session = aioboto3.Session()
        async with session.client(
            "s3",
            region_name=self.region,
            aws_access_key_id=S3_SETTINGS.S3_AWS_ACCESS_KEY_ID,
            aws_secret_access_key=S3_SETTINGS.S3_AWS_SECRET_ACCESS_KEY,
        ) as s3:
            file_path = f"{folder}/{get_kst_now().timestamp()}_{file.filename}"
            
            # S3 업로드 실행
            await s3.upload_fileobj(file.file, self.bucket_name, file_path)
            
            # 업로드된 파일의 공개 URL 반환
            return f"https://{self.bucket_name}.s3.{self.region}.amazonaws.com/{file_path}"

s3_uploader = S3Uploader()