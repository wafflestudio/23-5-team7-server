"""
관리자 기능 테스트 (AD01-AD11)
- GET /api/admin/events/{event_id}/bets
- PATCH /api/admin/users/{user_id}/role
- POST /api/admin/users/{user_id}/suspend
"""
from __future__ import annotations

import pytest
from httpx import AsyncClient
from datetime import timedelta
import json
import uuid
from jose import jwt
from snu_toto.tests.conftest import auth_header, assert_error_response
from snu_toto.app.core.date_utils import get_kst_now
# end imports


@pytest.fixture
def admin_user_id(admin_token: str) -> str:
    """admin_token에서 user_id 추출"""
    decoded = jwt.decode(
        admin_token, 
        key="", 
        algorithms=["HS256"], 
        options={"verify_signature": False}
    )
    return decoded["sub"]
# end def


# =============================================================================
# 이벤트 생성 헬퍼 (multipart/form-data)
# =============================================================================



@pytest.fixture
async def another_user_id(async_client: AsyncClient) -> str:
    """테스트용 다른 유저 생성 및 ID 반환"""
    unique_suffix = uuid.uuid4().hex[:8]
    
    response = await async_client.post(
        "/api/users",
        json={
            "email": f"another_{unique_suffix}@snu.ac.kr",
            "password": "testpassword123!",
            "nickname": f"다른유저_{unique_suffix}",
            "social_type": "LOCAL",
        },
    )
    assert response.status_code == 201
    return response.json()["user_id"]
# end def


# =============================================================================
# AD01: 이벤트 베팅 목록 조회 성공
# =============================================================================
@pytest.mark.asyncio
async def test_get_event_bets_for_admin_success_AD01(
    async_client: AsyncClient, admin_token: str, open_event_with_bets: str
):
    """AD01: 관리자가 이벤트 베팅 목록 조회 성공"""
    # Given
    event_id = open_event_with_bets
    
    # When
    response = await async_client.get(
        f"/api/admin/events/{event_id}/bets",
        headers=auth_header(admin_token),
    )
    
    # Then
    assert response.status_code == 200
    data = response.json()
    assert "event_info" in data
    assert "bets" in data
    assert "pagination" in data
    assert data["event_info"]["event_id"] == event_id
    assert len(data["bets"]) > 0
    assert data["bets"][0]["amount"] == 100
# end def


# =============================================================================
# AD02: 이벤트 베팅 조회 - 없는 이벤트
# =============================================================================
@pytest.mark.asyncio
async def test_get_event_bets_not_found_AD02(async_client: AsyncClient, admin_token: str):
    """AD02: 존재하지 않는 이벤트 베팅 조회 → ERR_009"""
    # Given
    non_existent_event_id = "non-existent-event-id"
    
    # When
    response = await async_client.get(
        f"/api/admin/events/{non_existent_event_id}/bets",
        headers=auth_header(admin_token),
    )
    
    # Then
    assert_error_response(response, 404, "ERR_009")
# end def


# =============================================================================
# AD03: 이벤트 베팅 조회 - 비관리자
# =============================================================================
@pytest.mark.asyncio
async def test_get_event_bets_non_admin_AD03(
    async_client: AsyncClient, auth_token: str, open_event_with_bets: str
):
    """AD03: 비관리자가 베팅 조회 시도 → ERR_030"""
    # Given
    event_id = open_event_with_bets
    
    # When
    response = await async_client.get(
        f"/api/admin/events/{event_id}/bets",
        headers=auth_header(auth_token),
    )
    
    # Then
    assert_error_response(response, 403, "ERR_030")
# end def


# =============================================================================
# AD04: 유저 권한 변경 성공
# =============================================================================
@pytest.mark.asyncio
async def test_update_user_role_success_AD04(
    async_client: AsyncClient, admin_token: str, another_user_id: str
):
    """AD04: 유저 권한 변경 성공"""
    # Given
    target_user_id = another_user_id
    
    # When
    response = await async_client.patch(
        f"/api/admin/users/{target_user_id}/role",
        json={"role": "ADMIN"},
        headers=auth_header(admin_token),
    )
    
    # Then
    assert response.status_code == 200
    data = response.json()
    assert data["role"] == "ADMIN"
# end def


# =============================================================================
# AD05: 유저 권한 변경 - 없는 유저
# =============================================================================
@pytest.mark.asyncio
async def test_update_user_role_not_found_AD05(async_client: AsyncClient, admin_token: str):
    """AD05: 존재하지 않는 유저 권한 변경 → ERR_042"""
    # Given
    non_existent_user_id = "non-existent-user-id"
    
    # When
    response = await async_client.patch(
        f"/api/admin/users/{non_existent_user_id}/role",
        json={"role": "ADMIN"},
        headers=auth_header(admin_token),
    )
    
    # Then
    assert_error_response(response, 404, "ERR_042")
# end def


# =============================================================================
# AD06: 유저 권한 변경 - 본인 변경
# =============================================================================
@pytest.mark.asyncio
async def test_update_user_role_self_AD06(async_client: AsyncClient, admin_token: str, admin_user_id: str):
    """AD06: 본인 권한 변경 시도 → ERR_043"""
    # Given
    self_user_id = admin_user_id
    
    # When
    response = await async_client.patch(
        f"/api/admin/users/{self_user_id}/role",
        json={"role": "USER"},
        headers=auth_header(admin_token),
    )
    
    # Then
    assert_error_response(response, 400, "ERR_043")
# end def


# =============================================================================
# AD07: 유저 권한 변경 - 비관리자
# =============================================================================
@pytest.mark.asyncio
async def test_update_user_role_non_admin_AD07(
    async_client: AsyncClient, auth_token: str, another_user_id: str
):
    """AD07: 비관리자가 권한 변경 시도 → ERR_030"""
    # Given
    target_user_id = another_user_id
    
    # When
    response = await async_client.patch(
        f"/api/admin/users/{target_user_id}/role",
        json={"role": "ADMIN"},
        headers=auth_header(auth_token),
    )
    
    # Then
    assert_error_response(response, 403, "ERR_030")
# end def


# =============================================================================
# AD08: 유저 정지 성공
# =============================================================================
@pytest.mark.asyncio
async def test_suspend_user_success_AD08(
    async_client: AsyncClient, admin_token: str, another_user_id: str
):
    """AD08: 유저 정지 성공"""
    # Given
    target_user_id = another_user_id
    
    # When
    response = await async_client.post(
        f"/api/admin/users/{target_user_id}/suspend",
        json={"suspension_hours": 24, "suspension_reason": "테스트 정지"},
        headers=auth_header(admin_token),
    )
    
    # Then
    assert response.status_code == 200
    data = response.json()
    assert data["user_id"] == target_user_id
    assert "suspension_info" in data
# end def


# =============================================================================
# AD09: 유저 정지 - 없는 유저
# =============================================================================
@pytest.mark.asyncio
async def test_suspend_user_not_found_AD09(async_client: AsyncClient, admin_token: str):
    """AD09: 존재하지 않는 유저 정지 → ERR_042"""
    # Given
    non_existent_user_id = "non-existent-user-id"
    
    # When
    response = await async_client.post(
        f"/api/admin/users/{non_existent_user_id}/suspend",
        json={"suspension_hours": 24, "suspension_reason": "테스트"},
        headers=auth_header(admin_token),
    )
    
    # Then
    assert_error_response(response, 404, "ERR_042")
# end def


# =============================================================================
# AD10: 유저 정지 - 본인 정지
# =============================================================================
@pytest.mark.asyncio
async def test_suspend_user_self_AD10(async_client: AsyncClient, admin_token: str, admin_user_id: str):
    """AD10: 본인 정지 시도 → ERR_044"""
    # Given
    self_user_id = admin_user_id
    
    # When
    response = await async_client.post(
        f"/api/admin/users/{self_user_id}/suspend",
        json={"suspension_hours": 24, "suspension_reason": "테스트"},
        headers=auth_header(admin_token),
    )
    
    # Then
    assert_error_response(response, 400, "ERR_044")
# end def


# =============================================================================
# AD11: 유저 정지 - 이미 정지됨
# =============================================================================
@pytest.mark.asyncio
async def test_suspend_user_already_suspended_AD11(
    async_client: AsyncClient, admin_token: str, another_user_id: str
):
    """AD11: 이미 정지된 유저 추가 정지 → ERR_045"""
    # Given - 먼저 정지
    target_user_id = another_user_id
    first_response = await async_client.post(
        f"/api/admin/users/{target_user_id}/suspend",
        json={"suspension_hours": 24, "suspension_reason": "첫 번째 정지"},
        headers=auth_header(admin_token),
    )
    assert first_response.status_code == 200
    
    # When - 다시 정지 시도
    response = await async_client.post(
        f"/api/admin/users/{target_user_id}/suspend",
        json={"suspension_hours": 24, "suspension_reason": "두 번째 정지"},
        headers=auth_header(admin_token),
    )
    
    # Then
    assert_error_response(response, 400, "ERR_045")
# end def


# =============================================================================
# AD12: 관리자 유저 목록 조회 성공
# =============================================================================
@pytest.mark.asyncio
async def test_get_admin_users_success_AD12(
    async_client: AsyncClient, admin_token: str, another_user_id: str
):
    """AD12: 관리자가 유저 목록 조회 성공"""
    # When
    response = await async_client.get(
        "/api/admin/users",
        headers=auth_header(admin_token),
    )
    
    # Then
    assert response.status_code == 200
    data = response.json()
    assert "users" in data
    assert "pagination" in data
    
    # 생성한 유저가 포함되어 있는지 확인
    found_user = next((u for u in data["users"] if u["user_id"] == another_user_id), None)
    assert found_user is not None
    assert found_user["points"] == 10000
# end def


# =============================================================================
# AD13: 관리자 유저 검색
# =============================================================================
@pytest.mark.asyncio
async def test_get_admin_users_with_search_AD13(
    async_client: AsyncClient, admin_token: str
):
    """AD13: 검색어로 유저 목록 필터링"""
    # When
    response = await async_client.get(
        "/api/admin/users?search=test",
        headers=auth_header(admin_token),
    )
    
    # Then
    assert response.status_code == 200
    data = response.json()
    assert "users" in data
# end def


# =============================================================================
# AD14: 관리자 유저 목록 조회 - 비관리자
# =============================================================================
@pytest.mark.asyncio
async def test_get_admin_users_non_admin_AD14(
    async_client: AsyncClient, auth_token: str
):
    """AD14: 비관리자가 유저 목록 조회 시도 → ERR_030"""
    # When
    response = await async_client.get(
        "/api/admin/users",
        headers=auth_header(auth_token),
    )
    
    # Then
    assert_error_response(response, 403, "ERR_030")
@pytest.mark.asyncio
async def test_cancel_event_refund_AD15(async_client: AsyncClient, admin_token: str, auth_token: str):
    """(AD15) 이벤트 취소 시 베팅금 환불 검증"""
    import json
    from snu_toto.app.core.date_utils import get_kst_now
    from datetime import timedelta
    
    # 1. 이벤트 생성 (Admin)
    start_at = get_kst_now() + timedelta(days=2) + timedelta(hours=1)
    end_at = start_at + timedelta(days=2)
    
    event_payload = {
        "title": "Refund Test Event",
        "start_at": start_at.isoformat(),
        "end_at": end_at.isoformat(),
        "options": [{"name": "A", "option_image_index": -1}, {"name": "B", "option_image_index": -1}],
        "images": []
    }
    
    empty_files = {"ignore_me": ("ignore.txt", b"", "text/plain")}
    
    create_res = await async_client.post(
        "/api/events", 
        data={"data": json.dumps(event_payload)},
        files=empty_files,
        headers=auth_header(admin_token)
    )
    assert create_res.status_code == 201
    event_id = create_res.json()["event_id"]
    option_id = create_res.json()["options"][0]["option_id"]
    
    # 2. OPEN
    await async_client.patch(
        f"/api/events/{event_id}/status",
        json={"status": "OPEN"},
        headers=auth_header(admin_token)
    )
    
    # 3. 유저 베팅 (1000포인트)
    profile_before = await async_client.get("/api/users/me/profile", headers=auth_header(auth_token))
    points_before_bet = profile_before.json()["points"]
    
    bet_amount = 1000
    bet_res = await async_client.post(
        f"/api/events/{event_id}/bets",
        json={"option_id": option_id, "bet_amount": bet_amount},
        headers=auth_header(auth_token)
    )
    assert bet_res.status_code == 201
    
    # 4. 베팅 후 잔액 확인
    p_after_bet = await async_client.get("/api/users/me/profile", headers=auth_header(auth_token))
    assert p_after_bet.json()["points"] == points_before_bet - bet_amount
    
    # 5. 이벤트 취소 (CANCELLED)
    cancel_res = await async_client.patch(
        f"/api/events/{event_id}/status",
        json={"status": "CANCELLED"},
        headers=auth_header(admin_token)
    )
    assert cancel_res.status_code == 200
    
    # 6. 환불 확인 (잔액 복구)
    p_after_cancel = await async_client.get("/api/users/me/profile", headers=auth_header(auth_token))
    assert p_after_cancel.json()["points"] == points_before_bet
    
    # 7. 베팅 상태 확인 (REFUNDED)
    my_bets = await async_client.get("/api/users/me/bets", headers=auth_header(auth_token))
    target_bet = next(b for b in my_bets.json()["bets"] if b["event_id"] == event_id)
    # The models/schemas usually use uppercase for Enum. Let's check string.
    # bet status in response might be string.
    assert target_bet["status"] == "REFUNDED"
    
    # 8. 포인트 내역 확인 (REFUND)
    history = await async_client.get("/api/users/me/point-history", headers=auth_header(auth_token))
    refund_entry = next((h for h in history.json()["history"] if h["reason"] == "REFUND"), None)
    assert refund_entry is not None
    assert refund_entry["change_amount"] == bet_amount
    assert refund_entry["points_after"] == points_before_bet
# end def
