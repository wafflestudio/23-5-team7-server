from fastapi import APIRouter, Depends, Query
from fastapi.responses import RedirectResponse
from snu_toto.app.auth.schemas import GoogleAuthResponse
from snu_toto.app.auth.services import AuthService
from snu_toto.app.auth.exceptions import MissingCodeException
from snu_toto.app.auth.dependencies import get_auth_service, google_client

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