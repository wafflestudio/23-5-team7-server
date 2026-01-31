from datetime import datetime
import pytz

# 한국 시간대 설정
KST = pytz.timezone('Asia/Seoul')

def get_kst_now():
    return datetime.now(KST).replace(tzinfo=None) # DB가 DATETIME(타임존 없음)일 경우를 위해 정보 제거