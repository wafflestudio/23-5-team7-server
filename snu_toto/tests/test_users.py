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
from unittest.mock import patch, AsyncMock
# end imports


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


# =============================================================================
# 2. 프로필 및 통계 조회 (GET /api/users/me/...)
# =============================================================================

@pytest.mark.asyncio
async def test_get_my_profile_U13(async_client: AsyncClient, auth_token: str, user_signup_data: dict):
    """(U13) 내 프로필 조회 - 성공"""
    response = await async_client.get("/api/users/me/profile", headers=auth_header(auth_token))
    
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == user_signup_data["email"]
    assert data["nickname"] == user_signup_data["nickname"]
    assert data["points"] == 10000
    assert data["role"] == "USER"

@pytest.mark.asyncio
async def test_get_my_stats_U14(async_client: AsyncClient, auth_token: str):
    """(U14) 내 통계 조회 - 초기 상태"""
    response = await async_client.get("/api/users/me/stats", headers=auth_header(auth_token))
    
    assert response.status_code == 200
    data = response.json()
    assert "bets" in data
    assert data["bets"]["total_bets_count"] == 0
    assert data["bets"]["win_rate"] == 0.0

@pytest.mark.asyncio
@patch("redis.asyncio.from_url", new_callable=AsyncMock)
async def test_get_my_ranking_U15(mock_from_url, async_client: AsyncClient, auth_token: str):
    """(U15) 내 랭킹 조회"""
    # Mock Redis setup
    mock_redis = AsyncMock()
    # Mock get method
    mock_redis.get.return_value = None # Cache miss -> DB fallback
    mock_redis.mget.return_value = ["100", "[{\"role\":\"user\"}]", "2024-01-01"]
    mock_redis.close = AsyncMock()
    mock_from_url.return_value = mock_redis

    response = await async_client.get("/api/users/me/ranking", headers=auth_header(auth_token))
    
    assert response.status_code == 200
    data = response.json()
    assert "rank" in data
    assert "percentile" in data

@pytest.mark.asyncio
async def test_get_my_bets_U16_initial(async_client: AsyncClient, auth_token: str):
    """(U16) 내 베팅 내역 조회 - 초기 상태 (빈 리스트)"""
    response = await async_client.get("/api/users/me/bets", headers=auth_header(auth_token))
    
    assert response.status_code == 200
    data = response.json()
    assert data["total_count"] == 0
    assert data["bets"] == []

@pytest.mark.asyncio
async def test_get_my_point_history_U17(async_client: AsyncClient, auth_token: str):
    """(U17) 내 포인트 내역 조회 - 가입 보너스 확인"""
    response = await async_client.get("/api/users/me/point-history", headers=auth_header(auth_token))
    
    assert response.status_code == 200
    data = response.json()
    assert len(data["history"]) >= 1
    
    # 가입 보너스 내역 찾기
    signup_bonus = next((h for h in data["history"] if h["reason"] == "SIGNUP"), None)
    assert signup_bonus is not None
    assert signup_bonus["change_amount"] == 10000

@pytest.mark.asyncio
@patch("redis.asyncio.from_url", new_callable=AsyncMock)
async def test_get_user_ranking_U18(mock_from_url, async_client: AsyncClient, auth_token: str):
    """(U18) 전체 랭킹 조회"""
    # Mock Redis setup
    mock_redis = AsyncMock()
    mock_redis.mget.return_value = ["10", "[]", "2024-01-01"] # total_count, top_list, updated_at
    mock_redis.close = AsyncMock()
    mock_from_url.return_value = mock_redis
    
    response = await async_client.get("/api/users/ranking", headers=auth_header(auth_token))
    
    assert response.status_code == 200
    data = response.json()
    
    assert "rankings" in data
    assert isinstance(data["rankings"], list)
    assert len(data["rankings"]) == 0

# =============================================================================
# 3. 유저 활동 통합 테스트 (Activity Flow)
# =============================================================================

@pytest.mark.asyncio
async def test_user_activity_flow_U19(async_client: AsyncClient, auth_token: str, admin_token: str):
    """(U19) 이벤트 생성 -> 베팅 -> 정보 업데이트 확인 -> 포인트 내역 확인"""
    from snu_toto.app.core.date_utils import get_kst_now
    from datetime import timedelta
    import json
    
    # 1. 이벤트 생성 (Admin) - Multipart 요청
    start_at = get_kst_now() + timedelta(days=3)
    end_at = start_at + timedelta(days=2)
    
    event_payload = {
        "title": "U19 Test Event",
        "options": [{"name": "Op1", "option_image_index": -1}, {"name": "Op2", "option_image_index": -1}],
        "start_at": start_at.isoformat(),
        "end_at": end_at.isoformat(),
        "images": []
    }
    
    # Dummy file for multipart
    empty_files = {"ignore_me": ("ignore.txt", b"", "text/plain")}
    
    create_res = await async_client.post(
        "/api/events", 
        data={"data": json.dumps(event_payload)},
        files=empty_files,
        headers=auth_header(admin_token)
    )
    assert create_res.status_code == 201, f"이벤트 생성 실패: {create_res.text}"
    event_id = create_res.json()["event_id"]
    option_id = create_res.json()["options"][0]["option_id"]
    
    # 2. 이벤트 OPEN (Admin) - 베팅 가능 상태로 변경
    status_res = await async_client.patch(
        f"/api/events/{event_id}/status",
        json={"status": "OPEN"},
        headers=auth_header(admin_token)
    )
    assert status_res.status_code == 200
    
    # 3. 베팅 전 상태 확인 (User)
    profile_before = await async_client.get("/api/users/me/profile", headers=auth_header(auth_token))
    initial_points = profile_before.json()["points"]
    
    # 4. 베팅 (User)
    bet_amount = 200
    bet_res = await async_client.post(
        f"/api/events/{event_id}/bets",
        json={"option_id": option_id, "bet_amount": bet_amount},
        headers=auth_header(auth_token)
    )
    assert bet_res.status_code == 201, f"베팅 실패: {bet_res.text}"
    
    # 5. 베팅 후 검증 (User)
    # A. 포인트 차감 확인
    profile_after = await async_client.get("/api/users/me/profile", headers=auth_header(auth_token))
    assert profile_after.json()["points"] == initial_points - bet_amount
    
    # B. 통계 업데이트 확인
    stats_res = await async_client.get("/api/users/me/stats", headers=auth_header(auth_token))
    stats_data = stats_res.json()
    assert stats_data["bets"]["total_bets_count"] == 1
    
    # C. 베팅 내역 확인
    bets_res = await async_client.get("/api/users/me/bets", headers=auth_header(auth_token))
    bets_data = bets_res.json()
    assert len(bets_data["bets"]) == 1
    assert bets_data["bets"][0]["event_id"] == event_id
    
    # D. 포인트 내역 확인 (CRITICAL: 여기서 버그 발견됨)
    history_res = await async_client.get("/api/users/me/point-history", headers=auth_header(auth_token))
    history_data = history_res.json()
    
    # 'BET' 사유 내역 찾기
    reasons = [h.get("reason") for h in history_data["history"]]
    bet_history = next((h for h in history_data["history"] if h["reason"] == "BET"), None)
    assert bet_history is not None, f"베팅 내역 없음. Found reasons: {reasons}"
    assert bet_history["change_amount"] == -bet_amount
    assert bet_history["points_after"] == initial_points - bet_amount
# end def
