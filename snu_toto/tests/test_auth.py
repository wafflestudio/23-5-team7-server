from __future__ import annotations

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
    response = await async_client.get("/api/auth/google/callback?code=valid_code")

    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "test@snu.ac.kr"
    assert data["needs_signup"] is True
    assert data["social_type"] == "GOOGLE"


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

    response = await async_client.get("/api/auth/google/callback?code=existing_user_code")

    assert response.status_code == 200
    data = response.json()
    assert data["access_token"] is not None
    assert data["needs_signup"] is False


@pytest.mark.asyncio
async def test_google_callback_missing_code(async_client: AsyncClient):
    """(A17) 콜백 code 누락"""
    response = await async_client.get("/api/auth/google/callback") # No code

    assert response.status_code == 400
    error = response.json()
    assert error["error_code"] == "ERR_020"



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
