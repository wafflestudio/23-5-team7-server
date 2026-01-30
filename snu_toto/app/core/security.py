import hashlib
from passlib.context import CryptContext
from datetime import datetime, timedelta
from jose import jwt
from snu_toto.app.core.config import AUTH_SETTINGS

# argon2를 기본 해시 알고리즘으로 설정
pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")

def get_password_hash(password: str) -> str:
    """Argon2를 사용하여 비밀번호 해싱"""
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """해시된 비밀번호와 평문 비교"""
    return pwd_context.verify(plain_password, hashed_password)

def create_jwt_token(user_id: int, purpose: str, expires_delta: timedelta, secret: str):
    """비밀키를 선택하여 JWT를 생성하는 함수"""
    expire = datetime.now() + expires_delta
    to_encode = {
        "sub": str(user_id),
        "purpose": purpose,
        "exp": expire
    }
    return jwt.encode(to_encode, secret, algorithm="HS256")

def create_verification_token(user_id: int):
    """이메일 인증 전용 토큰 (15분)"""
    return create_jwt_token(
        user_id=user_id,
        purpose="verification",
        expires_delta=timedelta(minutes=AUTH_SETTINGS.SHORT_SESSION_LIFESPAN),
        secret=AUTH_SETTINGS.ACCESS_TOKEN_SECRET
    )

def create_login_access_token(user_id: int):
    """일반 로그인용 액세스 토큰 (15분)"""
    return create_jwt_token(
        user_id=user_id,
        purpose="access",
        expires_delta=timedelta(minutes=AUTH_SETTINGS.SHORT_SESSION_LIFESPAN),
        secret=AUTH_SETTINGS.ACCESS_TOKEN_SECRET
    )

def create_refresh_token(user_id: int):
    """리프레시 토큰 (24시간)"""
    return create_jwt_token(
        user_id=user_id,
        purpose="refresh",
        expires_delta=timedelta(minutes=AUTH_SETTINGS.LONG_SESSION_LIFESPAN),
        secret=AUTH_SETTINGS.REFRESH_TOKEN_SECRET
    )

def decode_jwt_token(token: str, secret: str) -> dict:
    """JWT 토큰을 해독하고 페이로드를 반환 (만료 시 JWTError 발생)"""
    try:
        return jwt.decode(token, secret, algorithms=["HS256"])
    except jwt.JWTError:
        raise

def get_token_remaining_seconds(token: str, secret: str) -> int:
    """토큰의 남은 유효 시간을 초 단위로 반환"""
    try:
        payload = jwt.decode(token, secret, algorithms=["HS256"])
        exp = payload.get("exp")
        if not exp:
            return 0

        remaining = datetime.fromtimestamp(exp) - datetime.now()
        seconds = int(remaining.total_seconds())
        return max(seconds, 0)
    except jwt.JWTError:
        return 0

def get_email_hash(email: str) -> str:
    """이메일을 조회 가능한 형태로 해싱 (재가입 방지용)"""
    clean_email = email.strip()
    return hashlib.sha256(clean_email.encode()).hexdigest()