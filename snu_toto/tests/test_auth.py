from __future__ import annotations
from urllib.parse import parse_qs, urlparse

import pytest
from httpx import AsyncClient
from unittest.mock import MagicMock, AsyncMock
import unittest.mock

from snu_toto.app.main import app
from snu_toto.app.auth.dependencies import get_auth_service, get_verification_service
from snu_toto.app.auth.services import AuthService, VerificationService
from snu_toto.app.users.repositories import UserRepository
from snu_toto.app.auth.schemas import GoogleAuthResponse

# ============================================================================
# Mocks
# ============================================================================

class MockGoogleClient:
    async def get_user_info(self, code: str) -> dict:
        if code == "valid_code":
            return {
                "sub": "google_12345",
                "email": "test@snu.ac.kr",
                "name": "Google User",
                "picture": "http://image.com"
            }
        elif code == "existing_user_code":
            return {
                "sub": "google_existing",
                "email": "existing@snu.ac.kr",
                "name": "Existing User",
            }
        elif code == "invalid_email_code":
            return {
                "sub": "google_invalid",
                "email": "test@gmail.com", # Not SNU
            }
        else:
            raise Exception("Invalid Code")

    def get_auth_url(self):
        return "http://google.com/auth"

# ============================================================================
# Fixtures for Overrides
# ============================================================================

@pytest.fixture
def mock_google_client():
    return MockGoogleClient()

@pytest.fixture
def mock_verification_service():
    mock = AsyncMock(spec=VerificationService)
    # Default behaviors
    mock.check_rate_limit.return_value = True
    mock.create_verification_code.return_value = "123456"
    mock.verify_code.return_value = True
    mock.is_token_blacklisted.return_value = False  # 토큰이 블랙리스트에 없다고 가정
    mock.blacklist_token.return_value = None  # 블랙리스트 등록 성공
    return mock

@pytest.fixture(autouse=True)
def override_dependencies(db_session, mock_google_client, mock_verification_service):
    # Override get_auth_service to use MockGoogleClient
    def override_get_auth_service():
        user_repo = UserRepository(db_session)
        return AuthService(user_repo, mock_google_client)

    # Override get_verification_service to use MockVerificationService
    def override_get_verification_service():
        return mock_verification_service

    app.dependency_overrides[get_auth_service] = override_get_auth_service
    app.dependency_overrides[get_verification_service] = override_get_verification_service
    
    yield
    
    app.dependency_overrides.clear()


# ============================================================================
# 1-2. 로그인 (POST /api/auth/login)
# ============================================================================



@pytest.mark.asyncio
async def test_login_email_unverified(async_client: AsyncClient, user_signup_data):
    """(A02) 이메일 미인증 상태 로그인"""
    # Signup
    await async_client.post("/api/users", json=user_signup_data)

    # Login
    response = await async_client.post("/api/auth/login", json={
        "email": user_signup_data["email"],
        "password": user_signup_data["password"]
    })

    assert response.status_code == 403
    error = response.json()
    assert error["error_code"] == "ERR_015"
    assert "verification_token" in error # ERR_015 throws EmailVerificationRequiredException which has this

@pytest.mark.asyncio
async def test_login_success_verified(async_client: AsyncClient, user_signup_data, db_session):
    """(A01) 인증 완료 후 로그인 성공"""
    # Signup
    await async_client.post("/api/users", json=user_signup_data)

    # Manually verify user in DB
    from snu_toto.app.users.models import User
    from sqlalchemy import select, update
    
    stmt = select(User).where(User.email == user_signup_data["email"])
    result = await db_session.execute(stmt)
    user = result.scalar_one()
    
    user.is_snu_verified = True
    await db_session.commit()

    # Login
    response = await async_client.post("/api/auth/login", json={
        "email": user_signup_data["email"],
        "password": user_signup_data["password"]
    })

    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data


@pytest.mark.asyncio
async def test_login_wrong_password(async_client: AsyncClient, user_signup_data):
    """(A03) 잘못된 비밀번호"""
    await async_client.post("/api/users", json=user_signup_data)

    response = await async_client.post("/api/auth/login", json={
        "email": user_signup_data["email"],
        "password": "wrongpassword"
    })

    assert response.status_code == 401
    error = response.json()
    assert error["error_code"] == "ERR_014"


@pytest.mark.asyncio
async def test_login_user_not_found(async_client: AsyncClient):
    """(A04) 미가입 이메일"""
    response = await async_client.post("/api/auth/login", json={
        "email": "nobody@snu.ac.kr",
        "password": "password"
    })

    assert response.status_code == 401
    error = response.json()
    assert error["error_code"] == "ERR_014"


# ============================================================================
# 1-2-1. 구글 OAuth (GET /api/auth/google/callback)
# ============================================================================

@pytest.mark.asyncio
async def test_google_callback_new_user(async_client: AsyncClient):
    """(A15) 구글 콜백 성공 (신규 가입)"""
    response = await async_client.get(
        "/api/auth/google/callback?code=valid_code", 
        follow_redirects=False
    )

    assert response.status_code in [302, 307]

    # 쿼리 파라미터 확인
    location = response.headers.get("Location")
    parsed_url = urlparse(location)
    params = parse_qs(parsed_url.query)
    
    assert params.get("needs_signup") == ["true"]
    assert params.get("email") == ["test@snu.ac.kr"]
    assert params.get("social_type") == ["GOOGLE"]
    assert "social_id" in params

    # 쿠키가 설정되지 않는 것 확인
    assert "access_token" not in response.cookies
    assert "refresh_token" not in response.cookies


@pytest.mark.asyncio
async def test_google_callback_existing_user(async_client: AsyncClient, db_session):
    """(A16) 구글 콜백 성공 (기존 유저)"""
    # Pre-create existing google user using Repository or direct DB
    from snu_toto.app.users.models import User
    
    user = User(
        email="existing@snu.ac.kr",
        nickname="Existing",
        social_type="GOOGLE",
        social_id="google_existing",
        is_snu_verified=True
    )
    db_session.add(user)
    await db_session.commit()

    response = await async_client.get(
        "/api/auth/google/callback?code=existing_user_code", 
        follow_redirects=False
    )

    assert response.status_code in [302, 307]

    location = response.headers.get("Location")
    assert location.startswith("https://d55bqrug1d7zs.cloudfront.net/")
    
    parsed_url = urlparse(location)
    params = parse_qs(parsed_url.query)
    
    assert params.get("needs_signup") == ["false"]

    # 쿠키 검증
    assert "access_token" in response.cookies
    assert "refresh_token" in response.cookies
    
    # 쿠키 값 자체가 None이 아닌지도 확인
    assert response.cookies["access_token"] is not None
    assert response.cookies["refresh_token"] is not None


@pytest.mark.asyncio
async def test_google_callback_missing_code(async_client: AsyncClient):
    """(A17) 콜백 code 누락"""
    response = await async_client.get("/api/auth/google/callback", follow_redirects=False) # No code

    assert response.status_code in [302, 307]

    location = response.headers.get("Location")

    parsed_url = urlparse(location)
    params = parse_qs(parsed_url.query)

    assert params.get("error") == ["ERR_020"]
    assert "message" in params



@pytest.mark.asyncio
async def test_google_callback_invalid_email(async_client: AsyncClient):
    pass

@pytest.mark.asyncio
async def test_google_callback_auth_fail(async_client: AsyncClient, mock_google_client):
    pass

# ============================================================================
# 1-3. 인증코드 발송 (POST /api/auth/verify-email/send)
# ============================================================================

@pytest.mark.asyncio
async def test_send_verification_email_success(async_client: AsyncClient, user_signup_data, mock_verification_service):
    """(A05) 발송 성공"""
    # 1. 회원가입 (미인증 상태)
    await async_client.post("/api/users", json=user_signup_data)
    
    # 2. 로그인 시도 -> 403 Forbidden 및 verification_token 획득
    login_res = await async_client.post("/api/auth/login", json={
        "email": user_signup_data["email"],
        "password": user_signup_data["password"]
    })
    v_token = login_res.json().get("verification_token")
    
    headers = {"Authorization": f"Bearer {v_token}"}
    
    mock_verification_service.check_rate_limit.return_value = True
    
    # Mock SMTP send to avoid actual connection
    with unittest.mock.patch("aiosmtplib.send", new_callable=AsyncMock) as mock_send:
        response = await async_client.post("/api/auth/verify-email/send", headers=headers)
        
        assert response.status_code == 200
        mock_verification_service.create_verification_code.assert_called_once()
        mock_send.assert_called_once()


@pytest.mark.asyncio
async def test_send_email_no_token(async_client: AsyncClient):
    """(A06) 토큰 없음"""
    response = await async_client.post("/api/auth/verify-email/send")
    
    assert response.status_code == 401
    error = response.json()
    assert error["error_code"] == "ERR_004" # Or ERR_005 depending on implementation. Dependencies.py says UnauthenticatedException -> ?


@pytest.mark.asyncio
async def test_send_email_rate_limit(async_client: AsyncClient, user_signup_data, mock_verification_service):
    """(A09) 1분 내 재발송 (Rate Limit)"""
    # 1. 회원가입 & 토큰 획득
    await async_client.post("/api/users", json=user_signup_data)
    login_res = await async_client.post("/api/auth/login", json={
        "email": user_signup_data["email"],
        "password": user_signup_data["password"]
    })
    v_token = login_res.json().get("verification_token")
    headers = {"Authorization": f"Bearer {v_token}"}
    
    mock_verification_service.check_rate_limit.return_value = False # Limited
    
    response = await async_client.post("/api/auth/verify-email/send", headers=headers)
    
    assert response.status_code == 429
    error = response.json()
    assert error["error_code"] == "ERR_021"


# ============================================================================
# 1-4. 인증코드 확인 (POST /api/auth/verify-email/confirm)
# ============================================================================

@pytest.mark.asyncio
async def test_confirm_verification_success(async_client: AsyncClient, user_signup_data, mock_verification_service):
    """(A11) 확인 성공"""
    # 1. 회원가입 & 토큰 획득
    await async_client.post("/api/users", json=user_signup_data)
    login_res = await async_client.post("/api/auth/login", json={
        "email": user_signup_data["email"],
        "password": user_signup_data["password"]
    })
    v_token = login_res.json().get("verification_token")
    headers = {"Authorization": f"Bearer {v_token}"}
    
    payload = {"code": "123456"}
    
    mock_verification_service.verify_code.return_value = True
    
    response = await async_client.post("/api/auth/verify-email/confirm", json=payload, headers=headers)
    
    assert response.status_code == 200
    data = response.json()
    assert data["is_snu_verified"] is True


@pytest.mark.asyncio
async def test_confirm_verification_wrong_code(async_client: AsyncClient, user_signup_data, mock_verification_service):
    """(A12) 잘못된 코드"""
    # 1. 회원가입 & 토큰 획득
    await async_client.post("/api/users", json=user_signup_data)
    login_res = await async_client.post("/api/auth/login", json={
        "email": user_signup_data["email"],
        "password": user_signup_data["password"]
    })
    v_token = login_res.json().get("verification_token")
    headers = {"Authorization": f"Bearer {v_token}"}
    
    payload = {"code": "000000"}
    
    mock_verification_service.verify_code.return_value = False
    
    response = await async_client.post("/api/auth/verify-email/confirm", json=payload, headers=headers)
    
    assert response.status_code == 400
    error = response.json()
    assert error["error_code"] == "ERR_012"


# =============================================================================
# 1-7. 토큰 리프레시 (POST /api/auth/refresh)
# =============================================================================
from snu_toto.tests.conftest import auth_header, assert_error_response


@pytest.mark.asyncio
async def test_refresh_token_success_A19(async_client: AsyncClient, user_signup_data, db_session):
    """(A19) 토큰 리프레시 성공"""
    # 1. 회원가입
    await async_client.post("/api/users", json=user_signup_data)
    
    # 2. 인증 완료
    from snu_toto.app.users.models import User
    from sqlalchemy import select
    
    stmt = select(User).where(User.email == user_signup_data["email"])
    result = await db_session.execute(stmt)
    user = result.scalar_one()
    user.is_snu_verified = True
    await db_session.commit()
    
    # 3. 로그인
    login_res = await async_client.post("/api/auth/login", json={
        "email": user_signup_data["email"],
        "password": user_signup_data["password"]
    })
    
    assert login_res.status_code == 200
    refresh_token = login_res.json().get("refresh_token")
    
    # 4. 토큰 리프레시 요청 (쿠키로 전달)
    response = await async_client.post(
        "/api/auth/refresh",
        headers={"Cookie": f"refresh_token={refresh_token}"}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
# end def


@pytest.mark.asyncio
async def test_refresh_token_missing_A20(async_client: AsyncClient):
    """(A20) 리프레시 토큰 없음"""
    response = await async_client.post("/api/auth/refresh")
    
    assert_error_response(response, 401, "ERR_004")
# end def


# =============================================================================
# 1-8. 로그아웃 (POST /api/auth/logout)
# =============================================================================
@pytest.mark.asyncio
async def test_logout_success_A22(async_client: AsyncClient, user_signup_data, db_session):
    """(A22) 로그아웃 성공"""
    # 1. 회원가입
    await async_client.post("/api/users", json=user_signup_data)
    
    # 2. 인증 완료
    from snu_toto.app.users.models import User
    from sqlalchemy import select
    
    stmt = select(User).where(User.email == user_signup_data["email"])
    result = await db_session.execute(stmt)
    user = result.scalar_one()
    user.is_snu_verified = True
    await db_session.commit()
    
    # 3. 로그인
    login_res = await async_client.post("/api/auth/login", json={
        "email": user_signup_data["email"],
        "password": user_signup_data["password"]
    })
    
    access_token = login_res.json().get("access_token")
    refresh_token = login_res.json().get("refresh_token")
    
    # 4. 로그아웃
    response = await async_client.post(
        "/api/auth/logout",
        headers={
            "Authorization": f"Bearer {access_token}",
            "Cookie": f"refresh_token={refresh_token}"
        }
    )
    
    assert response.status_code == 200
    data = response.json()
    assert "message" in data
# end def


# =============================================================================
# 1-9. 회원 탈퇴 (POST /api/auth/withdraw)
# =============================================================================
@pytest.mark.asyncio
async def test_withdraw_success_A23(async_client: AsyncClient, user_signup_data, db_session):
    """(A23) 회원 탈퇴 성공"""
    # 1. 회원가입
    await async_client.post("/api/users", json=user_signup_data)
    
    # 2. 인증 완료
    from snu_toto.app.users.models import User
    from sqlalchemy import select
    
    stmt = select(User).where(User.email == user_signup_data["email"])
    result = await db_session.execute(stmt)
    user = result.scalar_one()
    user.is_snu_verified = True
    await db_session.commit()
    
    # 3. 로그인
    login_res = await async_client.post("/api/auth/login", json={
        "email": user_signup_data["email"],
        "password": user_signup_data["password"]
    })
    
    access_token = login_res.json().get("access_token")
    refresh_token = login_res.json().get("refresh_token")
    
    # 4. 회원 탈퇴
    response = await async_client.post(
        "/api/auth/withdraw",
        headers={
            "Authorization": f"Bearer {access_token}",
            "Cookie": f"refresh_token={refresh_token}"
        }
    )
    
    assert response.status_code == 200
    data = response.json()
    assert "message" in data
# end def


@pytest.mark.asyncio
async def test_withdraw_then_re_register_blocked_A24(async_client: AsyncClient, user_signup_data, db_session):
    """(A24) 탈퇴 후 30일 내 재가입 차단 (ERR_051)"""
    # 1. 회원가입
    await async_client.post("/api/users", json=user_signup_data)
    
    # 2. 인증 완료
    from snu_toto.app.users.models import User
    from sqlalchemy import select
    
    stmt = select(User).where(User.email == user_signup_data["email"])
    result = await db_session.execute(stmt)
    user = result.scalar_one()
    user.is_snu_verified = True
    await db_session.commit()
    
    # 3. 로그인
    login_res = await async_client.post("/api/auth/login", json={
        "email": user_signup_data["email"],
        "password": user_signup_data["password"]
    })
    
    access_token = login_res.json().get("access_token")
    refresh_token = login_res.json().get("refresh_token")
    
    # 4. 회원 탈퇴
    withdraw_res = await async_client.post(
        "/api/auth/withdraw",
        headers={
            "Authorization": f"Bearer {access_token}",
            "Cookie": f"refresh_token={refresh_token}"
        }
    )
    assert withdraw_res.status_code == 200, f"Withdraw failed: {withdraw_res.json()}"
    
    # 5. 같은 이메일로 재가입 시도 → ERR_051
    new_signup_data = {
        "email": user_signup_data["email"],
        "password": "newpassword123",
        "nickname": "새닉네임",
    }
    response = await async_client.post("/api/users", json=new_signup_data)
    
    assert_error_response(response, 409, "ERR_051")
# end def
