from __future__ import annotations

import pytest
from httpx import AsyncClient

# ============================================================================
# 1-1. 회원가입 (POST /api/users)
# ============================================================================


@pytest.mark.asyncio
async def test_create_user_success(async_client: AsyncClient):
    """(U01) 일반 회원가입 성공"""
    payload = {
        "email": "test_u01@snu.ac.kr",
        "password": "password123",
        "nickname": "U01User",
        "social_type": "LOCAL",
    }

    response = await async_client.post("/api/users", json=payload)
    
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == payload["email"]
    assert data["points"] == 10000
    assert data["social_type"] == "LOCAL"


@pytest.mark.asyncio
async def test_create_social_user_success(async_client: AsyncClient):
    """(U02) 소셜 회원가입 성공"""
    payload = {
        "email": "test_u02@snu.ac.kr",
        "nickname": "U02User",
        "social_type": "GOOGLE",
        "social_id": "google_12345",
    }

    response = await async_client.post("/api/users", json=payload)
    
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == payload["email"]
    assert data["social_type"] == "GOOGLE"


@pytest.mark.asyncio
async def test_create_user_not_snu_email(async_client: AsyncClient):
    """(U03) SNU 이메일 아님"""
    payload = {
        "email": "test@gmail.com",
        "password": "password123",
        "nickname": "NotSNU",
    }

    response = await async_client.post("/api/users", json=payload)
    
    assert response.status_code == 403
    error = response.json()
    assert error["error_code"] == "ERR_010"


@pytest.mark.asyncio
async def test_create_user_duplicate_email(async_client: AsyncClient):
    """(U04) 이메일 중복"""
    # 1. 먼저 생성
    first_user = {
        "email": "dup_email@snu.ac.kr",
        "password": "password123",
        "nickname": "FirstUser",
    }
    await async_client.post("/api/users", json=first_user)

    # 2. 같은 이메일로 다시 생성
    second_user = {
        "email": "dup_email@snu.ac.kr",
        "password": "password123",
        "nickname": "SecondUser",
    }
    response = await async_client.post("/api/users", json=second_user)
    
    assert response.status_code == 409
    error = response.json()
    assert error["error_code"] == "ERR_006"


@pytest.mark.asyncio
async def test_create_user_duplicate_nickname(async_client: AsyncClient):
    """(U05) 닉네임 중복"""
    # 1. 먼저 생성
    first_user = {
        "email": "user1@snu.ac.kr",
        "password": "password123",
        "nickname": "DupNick",
    }
    await async_client.post("/api/users", json=first_user)

    # 2. 같은 닉네임으로 다시 생성
    second_user = {
        "email": "user2@snu.ac.kr",
        "password": "password123",
        "nickname": "DupNick",
    }
    response = await async_client.post("/api/users", json=second_user)
    
    assert response.status_code == 409
    error = response.json()
    assert error["error_code"] == "ERR_007"


@pytest.mark.asyncio
async def test_create_user_duplicate_social_id(async_client: AsyncClient):
    """(U06) 소셜ID 중복"""
    # 1. 먼저 생성
    first_user = {
        "email": "social1@snu.ac.kr",
        "nickname": "Social1",
        "social_type": "GOOGLE",
        "social_id": "dup_social_id",
    }
    await async_client.post("/api/users", json=first_user)

    # 2. 같은 소셜ID로 다시 생성
    second_user = {
        "email": "social2@snu.ac.kr",
        "nickname": "Social2",
        "social_type": "GOOGLE",
        "social_id": "dup_social_id",
    }
    response = await async_client.post("/api/users", json=second_user)
    
    assert response.status_code == 409
    error = response.json()
    assert error["error_code"] == "ERR_018"


@pytest.mark.asyncio
async def test_create_user_local_missing_password(async_client: AsyncClient):
    """(U07) LOCAL인데 password 누락"""
    payload = {
        "email": "nopass@snu.ac.kr",
        "nickname": "NoPass",
        "social_type": "LOCAL",
        # password missing
    }

    response = await async_client.post("/api/users", json=payload)
    
    assert response.status_code == 400
    error = response.json()
    assert error["error_code"] == "ERR_016"


@pytest.mark.asyncio
async def test_create_user_social_missing_social_id(async_client: AsyncClient):
    """(U08) SOCIAL인데 social_id 누락"""
    payload = {
        "email": "nosocialid@snu.ac.kr",
        "nickname": "NoSocialId",
        "social_type": "KAKAO",
        # social_id missing
    }

    response = await async_client.post("/api/users", json=payload)
    
    assert response.status_code == 400
    error = response.json()
    assert error["error_code"] == "ERR_017"


# =============================================================================
# 1-2. 닉네임 변경 (PATCH /api/users/me/nickname)
# =============================================================================
from snu_toto.tests.conftest import auth_header, assert_error_response


@pytest.mark.asyncio
async def test_update_nickname_success_U09(async_client: AsyncClient, auth_token: str):
    """(U09) 닉네임 변경 성공"""
    new_nickname = "새닉네임"
    response = await async_client.patch(
        "/api/users/me/nickname",
        json={"nickname": new_nickname},
        headers=auth_header(auth_token)
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["nickname"] == new_nickname
# end def


@pytest.mark.asyncio
async def test_update_nickname_duplicate_U10(async_client: AsyncClient, auth_token: str):
    """(U10) 닉네임 중복"""
    other_user = {
        "email": "other@snu.ac.kr",
        "password": "password123",
        "nickname": "사용중닉네임",
    }
    await async_client.post("/api/users", json=other_user)
    
    response = await async_client.patch(
        "/api/users/me/nickname",
        json={"nickname": "사용중닉네임"},
        headers=auth_header(auth_token)
    )
    
    assert_error_response(response, 409, "ERR_007")
# end def


# =============================================================================
# 1-3. 비밀번호 변경 (PATCH /api/users/me/password)
# =============================================================================
@pytest.mark.asyncio
async def test_update_password_success_U11(async_client: AsyncClient, auth_token: str, user_signup_data: dict):
    """(U11) 비밀번호 변경 성공"""
    response = await async_client.patch(
        "/api/users/me/password",
        json={
            "current_password": user_signup_data["password"],
            "new_password": "newpassword456"
        },
        headers=auth_header(auth_token)
    )
    
    assert response.status_code == 200
    data = response.json()
    assert "message" in data
# end def


@pytest.mark.asyncio
async def test_update_password_wrong_current_U12(async_client: AsyncClient, auth_token: str):
    """(U12) 현재 비밀번호 틀림"""
    response = await async_client.patch(
        "/api/users/me/password",
        json={
            "current_password": "wrongpassword",
            "new_password": "newpassword456"
        },
        headers=auth_header(auth_token)
    )
    
    assert_error_response(response, 401, "ERR_014")
# end def
