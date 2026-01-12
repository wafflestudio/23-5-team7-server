from passlib.context import CryptContext

# argon2를 기본 해시 알고리즘으로 설정
pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")

def get_password_hash(password: str) -> str:
    """Argon2를 사용하여 비밀번호 해싱"""
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """해시된 비밀번호와 평문 비교"""
    return pwd_context.verify(plain_password, hashed_password)