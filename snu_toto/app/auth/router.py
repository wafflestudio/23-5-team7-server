from fastapi import APIRouter, Depends, Query, BackgroundTasks
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession
from snu_toto.app.auth.schemas import EmailConfirmRequest, EmailConfirmResponse, EmailSendResponse, GoogleAuthResponse, LoginRequest, LoginResponse
from snu_toto.app.auth.services import AuthService, VerificationService
from snu_toto.app.auth.exceptions import MissingCodeException
from snu_toto.app.auth.dependencies import get_auth_service, google_client
from snu_toto.app.auth.dependencies import get_current_unverified_user, get_verification_service
from snu_toto.app.auth.utils import EmailSender
from snu_toto.app.core.database import get_db_session
from snu_toto.app.auth.exceptions import (
    AlreadyVerifiedException,
    RateLimitException,
    InvalidCodeException,
)



auth_router = APIRouter()

@auth_router.get("/google/login")
async def google_login():
    """구글 로그인 페이지로 리다이렉트 (dependencies의 google_client 사용)"""
    return RedirectResponse(google_client.get_auth_url())

@auth_router.get("/google/callback", response_model=GoogleAuthResponse)
async def google_callback(
    code: str = Query(None, description="구글 인가 코드"),
    auth_service: AuthService = Depends(get_auth_service)
):
    """구글 인증 콜백 처리 (인가 코드로 로그인/가입 판단)"""
    if not code:
        raise MissingCodeException()
        
    return await auth_service.handle_google_callback(code)


@auth_router.post("/verify-email/send")
async def send_verification_email(
    background_tasks: BackgroundTasks,
    user = Depends(get_current_unverified_user),
    v_service: VerificationService = Depends(get_verification_service)
):
    """인증번호 발송"""

    # 이미 인증된 유저인지 확인
    if user.is_snu_verified:
        raise AlreadyVerifiedException()

    # 1분 이내 재발송 제한 확인
    if not await v_service.check_rate_limit(str(user.user_id)):
        raise RateLimitException()

    # 인증 번호 생성 및 Redis 저장
    code = await v_service.create_verification_code(str(user.user_id))

    # 이메일 발송
    # BackgroundTasks를 쓰면 메일 보내는 동안 유저가 기다리지 않아도 됨
    background_tasks.add_task(EmailSender.send_verification_email, user.email, code)

    return EmailSendResponse()


@auth_router.post("/verify-email/confirm")
async def confirm_verification_code(
    body: EmailConfirmRequest,
    user = Depends(get_current_unverified_user),
    v_service: VerificationService = Depends(get_verification_service),
    db: AsyncSession = Depends(get_db_session)
):
    """인증번호 확인"""

    input_code = body.code
    
    # 번호 검증
    is_valid = await v_service.verify_code(str(user.user_id), input_code)
    
    if not is_valid:
        # 번호가 틀렸거나 만료된 경우
        raise InvalidCodeException()

    # DB 업데이트 (인증 완료 처리)
    user.is_snu_verified = True
    await db.commit() # 실제 DB에 저장

    return EmailConfirmResponse(
        email=user.email,
        is_snu_verified=user.is_snu_verified
    )


@auth_router.post("/login", response_model=LoginResponse)
async def login(
    body: LoginRequest,
    auth_service: AuthService = Depends(get_auth_service)
):
    """일반 로그인"""
    return await auth_service.authenticate_user(body.email, body.password)