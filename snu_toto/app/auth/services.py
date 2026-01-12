from snu_toto.app.auth.providers.google import GoogleAuthClient
from snu_toto.app.auth.schemas import GoogleAuthResponse, GoogleUserResult
from snu_toto.app.users.exceptions import EmailAlreadyExistsException, OnlySnuEmailAllowedException
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
            # TODO: 실제 JWT 발급 로직 호출 구현되면 수정
            return GoogleAuthResponse(
                message="로그인 성공",
                access_token="valid_jwt_token",
                refresh_token="valid_refresh_token",
                user=GoogleUserResult(
                    email=user.email,
                    nickname=user.nickname,
                    is_snu_verified=user.is_snu_verified
                )
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