from __future__ import annotations

import pytest
from httpx import AsyncClient
from datetime import datetime, timedelta
from unittest.mock import patch, AsyncMock

# ============================================================================
# 2-3. 통합 테스트 (I01-I05)
# ============================================================================

@pytest.mark.asyncio
async def test_integration_signup_verify_login(
    async_client: AsyncClient, 
    mock_verification_service
):
    """(I01) 회원가입 → 인증 → 로그인"""
    from snu_toto.app.main import app
    from snu_toto.app.auth.dependencies import get_verification_service
    
    # Override dependency using function (safer than lambda for Depends inspection)
    def override_get_verification_service():
        return mock_verification_service
    
    app.dependency_overrides[get_verification_service] = override_get_verification_service
    
    # Patch SMTP send to prevent connection errors even if DI override fails transiently
    # But ideally DI override should work.
    with patch("aiosmtplib.send", new_callable=AsyncMock) as mock_send:
        try:
            # 1. Signup
            signup_payload = {
                "email": "i01_user@snu.ac.kr",
                "password": "password123",
                "nickname": "IntegrationUser",
                "social_type": "LOCAL"
            }
            signup_res = await async_client.post("/api/users", json=signup_payload)
            assert signup_res.status_code == 201

            # 2. Login (Before Verify) -> 403
            login_payload = {
                "email": signup_payload["email"],
                "password": signup_payload["password"]
            }
            login_res_1 = await async_client.post("/api/auth/login", json=login_payload)
            assert login_res_1.status_code == 403
            token = login_res_1.json().get("verification_token")
            assert token is not None

            # 3. Send Verification Code
            headers = {"Authorization": f"Bearer {token}"}
            send_res = await async_client.post("/api/auth/verify-email/send", headers=headers)
            assert send_res.status_code == 200

            # 4. Confirm Code
            # Mock verify_code to return True
            mock_verification_service.verify_code.return_value = True
            confirm_payload = {"code": "123456"}
            confirm_res = await async_client.post("/api/auth/verify-email/confirm", json=confirm_payload, headers=headers)
            assert confirm_res.status_code == 200
            assert confirm_res.json()["is_snu_verified"] is True

            # 5. Login (After Verify) -> 200
            login_res_2 = await async_client.post("/api/auth/login", json=login_payload)
            assert login_res_2.status_code == 200
            assert "access_token" in login_res_2.json()
        finally:
            app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_integration_event_bet_settle(async_client: AsyncClient, admin_token: str):
    """(I02, I03) 이벤트 생성 -> 오픈 -> 베팅 -> 정산"""
    # Requires Post Event implementation
    pass
