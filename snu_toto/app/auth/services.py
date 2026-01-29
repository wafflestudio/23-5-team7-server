from datetime import datetime
import random
import string
import jwt
from redis.asyncio import Redis

from snu_toto.app.auth.exceptions import EmailVerificationRequiredException, InvalidCredentialsException, InvalidTokenException, SuspendedUserException
from snu_toto.app.auth.providers.google import GoogleAuthClient
from snu_toto.app.auth.schemas import GoogleAuthResponse, GoogleUserResult, LoginResponse, UserLoginResult
from snu_toto.app.core.config import AUTH_SETTINGS
from snu_toto.app.core.security import create_login_access_token, create_refresh_token, create_verification_token, decode_jwt_token, get_email_hash, verify_password
from snu_toto.app.users.exceptions import EmailAlreadyExistsException, OnlySnuEmailAllowedException
from snu_toto.app.users.models import User
from snu_toto.app.users.repositories import UserRepository


class AuthService:
    def __init__(self, user_repo: UserRepository, google_client: GoogleAuthClient):
        self.user_repo = user_repo
        self.google_client = google_client

    async def handle_google_callback(self, code: str):
        # 1. 구글 정보 획득
        user_info = await self.google_client.get_user_info(code)
        email = user_info.get("email")
        social_id = user_info.get("sub")

        # 2. 도메인 검증
        if not email or not email.endswith("@snu.ac.kr"):
            raise OnlySnuEmailAllowedException()

        # 3. 기존 소셜 유저 확인
        user = await self.user_repo.get_by_social_id("GOOGLE", social_id)
        if user:
            await self._check_user_suspension(user)

            access_token = create_login_access_token(user.user_id)
            refresh_token = create_refresh_token(user.user_id)
            return GoogleAuthResponse(
                message="로그인 성공",
                access_token=access_token,
                refresh_token=refresh_token,
                is_snu_verified=True, # 구글 소셜 로그인은 이메일 인증을 할 필요 없음
                needs_signup=False
            )

        # 4. 이메일 중복 체크 (일반 가입 유저 확인)
        existing_user = await self.user_repo.get_by_email(email)
        if existing_user:
            raise EmailAlreadyExistsException()

        # 5. 신규 유저 응답
        return GoogleAuthResponse(
            message="신규 유저입니다. 가입을 위해 닉네임을 입력해주세요.",
            email=email,
            social_id=social_id,
            social_type="GOOGLE",
            needs_signup=True
        )
    
    async def authenticate_user(self, email: str, password: str):
        """비밀번호 검증, 이메일 인증 여부 확인"""
        user = await self.user_repo.get_by_email(email)
        if not user:
            raise InvalidCredentialsException()

        if not verify_password(password, user.hashed_password):
            raise InvalidCredentialsException()

        if not user.is_snu_verified:
            # 인증 안 된 유저에게는 15분짜리 임시 토큰을 생성해서 던짐
            v_token = create_verification_token(user.user_id)
            raise EmailVerificationRequiredException(verification_token=v_token)
        
        await self._check_user_suspension(user)

        # 로그인 성공 - 토큰 생성
        access_token = create_login_access_token(user.user_id)
        refresh_token = create_refresh_token(user.user_id)

        return LoginResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            user=UserLoginResult(
                user_id=user.user_id,
                nickname=user.nickname,
                is_snu_verified=user.is_snu_verified,
                points=user.points
            )
        )
    
    async def _check_user_suspension(self, user: User):
        """정지 여부 확인 및 자동 복구 공통 로직"""
        if not user.suspended_until:
            return

        if datetime.now() < user.suspended_until:
            raise SuspendedUserException(
                suspension_reason=user.suspension_reason,
                suspended_until=user.suspended_until
            )
        
        # 기한 만료 시 복구
        await self.user_repo.clear_suspension(user)
    
    async def refresh_tokens(self, refresh_token: str):
        """리프레시 토큰 검증 및 새로운 토큰 쌍 발급"""
        try:
            # security 유틸리티를 사용하여 토큰 해독
            payload = decode_jwt_token(refresh_token, AUTH_SETTINGS.REFRESH_TOKEN_SECRET)
            
            user_id = payload.get("sub")
            purpose = payload.get("purpose")

            # 용도 확인
            if purpose != "refresh":
                raise InvalidTokenException()

            # DB 작업
            user = await self.user_repo.get_by_id(user_id)
            if not user:
                raise InvalidTokenException()

            # 정지 여부 확인
            await self._check_user_suspension(user)

            # 새로운 토큰 생성
            new_access = create_login_access_token(user.user_id)
            new_refresh = create_refresh_token(user.user_id)

            return new_access, new_refresh, user

        except jwt.JWTError:
            raise InvalidTokenException()
        
    async def execute_withdrawal(self, user: User):
        """회원탈퇴 비즈니스 프로세스 실행"""
        # 이메일 해싱 처리
        hashed_email = get_email_hash(user.email)
        
        await self.user_repo.anonymize_and_withdraw(user, hashed_email)

class VerificationService:
    def __init__(self, redis: Redis):
        self.redis = redis
        self.CODE_EXPIRE_SEC = 300  # 5분 동안만 번호가 유효함
        self.LIMIT_EXPIRE_SEC = 60  # 1분 안에 다시 메일을 보낼 수 없음

    async def create_verification_code(self, user_id: str) -> str:
        """6자리 랜덤 인증 번호를 만들고 Redis에 저장"""
        code = "".join(random.choices(string.digits, k=6))
        code_key = f"verify:code:{user_id}"
        
        # Redis에 저장 (Key: verify:code:{user_id} / Value: code)
        await self.redis.setex(
            code_key, 
            self.CODE_EXPIRE_SEC, 
            code
        )
        return code

    async def check_rate_limit(self, user_id: str) -> bool:
        """인증메일 재발송 간격 확인"""
        limit_key = f"mail_limit:{user_id}"
        exists = await self.redis.exists(limit_key)
        
        if exists:
            return False  # 이미 1분 내에 요청한 적이 있음 (거절)
            
        # 1분짜리 제한 표시를 Redis에 남김
        await self.redis.setex(limit_key, self.LIMIT_EXPIRE_SEC, "locked")
        return True

    async def verify_code(self, user_id: str, input_code: str) -> bool:
        """입력한 번호가 Redis에 있는 번호와 일치하는지 확인"""
        code_key = f"verify:code:{user_id}"
        saved_code = await self.redis.get(code_key)

        if saved_code is None:
            return False # 번호가 없거나 5분이 지나서 삭제됨
            
        if saved_code.decode('utf-8') == input_code:
            # 인증 성공 시, 번호를 재사용 못하게 바로 삭제
            await self.redis.delete(code_key)
            return True
            
        return False

    async def blacklist_token(self, token: str, expires_in: int):
        """토큰을 블랙리스트에 등록 (TTL은 토큰의 남은 수명만큼)"""
        key = f"blacklist:{token}"
        await self.redis.setex(key, expires_in, "revoked")

    async def is_token_blacklisted(self, token: str) -> bool:
        """해당 토큰이 블랙리스트에 있는지 확인"""
        key = f"blacklist:{token}"
        return await self.redis.exists(key)