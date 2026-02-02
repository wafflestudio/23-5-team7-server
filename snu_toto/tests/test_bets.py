from __future__ import annotations

import pytest
from httpx import AsyncClient
from datetime import datetime, timedelta
import json
import uuid
from snu_toto.app.core.date_utils import get_kst_now
from snu_toto.tests.conftest import auth_header, assert_error_response, multipart_headers, EMPTY_FILES

# =============================================================================
# Helper Fixtures for Bets
# =============================================================================

@pytest.fixture
async def open_event_id(async_client: AsyncClient, admin_token: str) -> str:
    """OPEN 상태의 이벤트를 생성하고 ID 반환"""
    start_at = (get_kst_now() + timedelta(days=2) + timedelta(hours=1)).isoformat()
    end_at = (get_kst_now() + timedelta(days=3) + timedelta(hours=2)).isoformat()
    
    event_data = {
        "title": f"베팅 테스트용 오픈 이벤트 {uuid.uuid4()}",
        "description": "오픈됨",
        "start_at": start_at,
        "end_at": end_at,
        "options": [
            {"name": "옵션A", "option_image_index": -1},
            {"name": "옵션B", "option_image_index": -1}
        ],
        "images": []
    }
    # 1. Create (READY)
    create_res = await async_client.post(
        "/api/events",
        data={"data": json.dumps(event_data)},
        files=EMPTY_FILES,
        headers=auth_header(admin_token)
    )
    event_id = create_res.json()["event_id"]
    
    # 2. Update to OPEN
    await async_client.patch(
        f"/api/events/{event_id}/status",
        json={"status": "OPEN"},
        headers=auth_header(admin_token)
    )
    return event_id

@pytest.fixture
async def closed_event_id(async_client: AsyncClient, admin_token: str) -> str:
    """CLOSED 상태의 이벤트를 생성하고 ID 반환"""
    start_at = (get_kst_now() + timedelta(days=2) + timedelta(hours=1)).isoformat()
    end_at = (get_kst_now() + timedelta(days=3) + timedelta(hours=2)).isoformat()
    
    event_data = {
        "title": f"베팅 테스트용 마감 이벤트 {uuid.uuid4()}",
        "description": "마감됨",
        "start_at": start_at,
        "end_at": end_at,
        "options": [{"name": "A", "option_image_index": -1}, {"name": "B", "option_image_index": -1}]
    }
    # 1. Create (READY)
    create_res = await async_client.post(
        "/api/events",
        data={"data": json.dumps(event_data)},
        files=EMPTY_FILES,
        headers=auth_header(admin_token)
    )
    event_id = create_res.json()["event_id"]
    
    # 2. Update to OPEN then CLOSED
    await async_client.patch(f"/api/events/{event_id}/status", json={"status": "OPEN"}, headers=auth_header(admin_token))
    await async_client.patch(f"/api/events/{event_id}/status", json={"status": "CLOSED"}, headers=auth_header(admin_token))
    
    return event_id

# =============================================================================
# 1. 베팅 생성 (POST /api/events/{id}/bets)
# =============================================================================

@pytest.mark.asyncio
async def test_create_bet_success_B01(async_client: AsyncClient, auth_token: str, open_event_id: str):
    """B01: 베팅 성공 (201 Created)"""
    # 1. Get Event to find option_id
    event_res = await async_client.get(f"/api/events/{open_event_id}")
    options = event_res.json()["options"]
    option_id = options[0]["option_id"] # First option
    
    bet_payload = {
        "option_id": option_id,
        "bet_amount": 1000
    }
    
    response = await async_client.post(
        f"/api/events/{open_event_id}/bets",
        json=bet_payload,
        headers=auth_header(auth_token)
    )
    
    assert response.status_code == 201
    data = response.json()
    assert data["bet_amount"] == 1000
    assert data["option_id"] == option_id
    assert "bet_id" in data
    
    # Verify User Points reduced (Optional, but good for verification)
    me_res = await async_client.get("/api/users/me/profile", headers=auth_header(auth_token))
    # Initial 10000 - 1000 = 9000
    assert me_res.json()["points"] == 9000

@pytest.mark.asyncio
async def test_create_bet_insufficient_balance_B02(async_client: AsyncClient, auth_token: str, open_event_id: str):
    """B02: 잔액 부족 (ERR_038)"""
    event_res = await async_client.get(f"/api/events/{open_event_id}")
    option_id = event_res.json()["options"][0]["option_id"]
    
    # Try betting more than 10000
    bet_payload = {
        "option_id": option_id,
        "bet_amount": 20000 
    }
    
    response = await async_client.post(
        f"/api/events/{open_event_id}/bets",
        json=bet_payload,
        headers=auth_header(auth_token)
    )
    
    assert_error_response(response, 400, "ERR_038")

@pytest.mark.asyncio
async def test_create_bet_duplicate_B03(async_client: AsyncClient, auth_token: str, open_event_id: str):
    """B03: 중복 베팅 (ERR_041)"""
    event_res = await async_client.get(f"/api/events/{open_event_id}")
    options = event_res.json()["options"]
    option_id_1 = options[0]["option_id"]
    option_id_2 = options[1]["option_id"]
    
    # 1. First Bet Success
    await async_client.post(
        f"/api/events/{open_event_id}/bets",
        json={"option_id": option_id_1, "bet_amount": 100},
        headers=auth_header(auth_token)
    )
    
    # 2. Second Bet Fail (Same Event)
    response = await async_client.post(
        f"/api/events/{open_event_id}/bets",
        json={"option_id": option_id_2, "bet_amount": 100}, # Different option, but same event -> Fail
        headers=auth_header(auth_token)
    )
    
    assert_error_response(response, 409, "ERR_041") # Already betted on this event

@pytest.mark.asyncio
async def test_create_bet_not_open_B04(async_client: AsyncClient, auth_token: str, closed_event_id: str):
    """B04: OPEN 상태가 아닌 이벤트에 베팅 (ERR_040)"""
    # Event is CLOSED
    event_res = await async_client.get(f"/api/events/{closed_event_id}")
    option_id = event_res.json()["options"][0]["option_id"]
    
    response = await async_client.post(
        f"/api/events/{closed_event_id}/bets",
        json={"option_id": option_id, "bet_amount": 100},
        headers=auth_header(auth_token)
    )
    
    assert_error_response(response, 409, "ERR_040") # Event not open

@pytest.mark.asyncio
async def test_create_bet_event_not_found_B05(async_client: AsyncClient, auth_token: str):
    """B05: 없는 이벤트 (ERR_009)"""
    import uuid
    random_id = str(uuid.uuid4())
    
    response = await async_client.post(
        f"/api/events/{random_id}/bets",
        json={"option_id": str(uuid.uuid4()), "bet_amount": 100},
        headers=auth_header(auth_token)
    )
    assert_error_response(response, 404, "ERR_009")

@pytest.mark.asyncio
async def test_create_bet_option_not_found_B06(async_client: AsyncClient, auth_token: str, open_event_id: str):
    """B06: 해당 이벤트에 없는 옵션 ID (ERR_039)"""
    import uuid
    response = await async_client.post(
        f"/api/events/{open_event_id}/bets",
        json={"option_id": str(uuid.uuid4()), "bet_amount": 100}, # Random UUID
        headers=auth_header(auth_token)
    )
    assert_error_response(response, 404, "ERR_039")

# =============================================================================
# 2. 내 베팅 조회 (GET /api/users/me/bets)
# =============================================================================

@pytest.mark.asyncio
async def test_get_my_bets_B08(async_client: AsyncClient, auth_token: str, open_event_id: str):
    """B08: 내 베팅 목록 조회 성공"""
    # Create a bet first
    event_res = await async_client.get(f"/api/events/{open_event_id}")
    option_id = event_res.json()["options"][0]["option_id"]
    await async_client.post(
        f"/api/events/{open_event_id}/bets",
        json={"option_id": option_id, "bet_amount": 500},
        headers=auth_header(auth_token)
    )
    
    # Get bets
    response = await async_client.get("/api/users/me/bets", headers=auth_header(auth_token))
    
    assert response.status_code == 200
    data = response.json()
    assert "bets" in data
    bets = data["bets"]
    assert isinstance(bets, list)
    assert len(bets) >= 1
    # Note: Event title might contain UUID suffix now check logic or just checking existence
    assert bets[0]["amount"] == 500


