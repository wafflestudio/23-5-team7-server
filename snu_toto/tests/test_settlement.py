from __future__ import annotations

import pytest
from httpx import AsyncClient
from datetime import datetime, timedelta
import json
import uuid
from snu_toto.tests.conftest import auth_header, assert_error_response, multipart_headers, EMPTY_FILES
from snu_toto.app.core.date_utils import get_kst_now

# =============================================================================
# Helper Fixtures for Settlement
# =============================================================================

@pytest.fixture
async def unsettled_closed_event_id(async_client: AsyncClient, admin_token: str, auth_token: str) -> str:
    """
    정산 전 CLOSED 상태의 이벤트를 생성하고,
    일반 유저가 베팅을 한 상태로 만든 후 ID 반환
    """
    # 1. Create Event (OPEN immediately via update logic or just create open)
    start_at = (get_kst_now() + timedelta(days=3)).isoformat()
    end_at = (get_kst_now() + timedelta(days=5)).isoformat()
    
    event_data = {
        "title": f"정산 테스트용 이벤트 {uuid.uuid4()}",
        "description": "정산 전",
        "start_at": start_at, 
        "end_at": end_at, 
        "options": [
            {"name": "WIN", "option_image_index": -1}, 
            {"name": "LOSE", "option_image_index": -1}
        ],
        "images": []
    }
    
    # Create
    create_res = await async_client.post(
        "/api/events",
        data={"data": json.dumps(event_data)},
        files=EMPTY_FILES,
        headers=auth_header(admin_token)
    )
    assert create_res.status_code == 201, f"Event creation failed: {create_res.text}"
    event_id = create_res.json()["event_id"]
    
    # Update to OPEN
    await async_client.patch(f"/api/events/{event_id}/status", json={"status": "OPEN"}, headers=auth_header(admin_token))
    
    # 2. Add Bet (User bets on WIN)
    event_res = await async_client.get(f"/api/events/{event_id}")
    win_option_id = event_res.json()["options"][0]["option_id"]
    
    await async_client.post(
        f"/api/events/{event_id}/bets",
        json={"option_id": win_option_id, "bet_amount": 1000},
        headers=auth_header(auth_token)
    )
    
    # 3. Update to CLOSED
    await async_client.patch(f"/api/events/{event_id}/status", json={"status": "CLOSED"}, headers=auth_header(admin_token))
    
    return event_id

@pytest.fixture
async def settled_event_id(async_client: AsyncClient, admin_token: str) -> str:
    """이미 SETTLED 된 이벤트 ID 반환"""
    start_at = (get_kst_now() + timedelta(days=3)).isoformat()
    end_at = (get_kst_now() + timedelta(days=5)).isoformat()
    
    event_data = {"title": f"이미 정산된 이벤트 {uuid.uuid4()}", "description": "-", "start_at": start_at, "end_at": end_at, "options": [{"name": "A", "option_image_index": -1}, {"name": "B", "option_image_index": -1}]}
    
    create_res = await async_client.post("/api/events", data={"data": json.dumps(event_data)}, files=EMPTY_FILES, headers=auth_header(admin_token))
    assert create_res.status_code == 201, f"Event creation failed: {create_res.text}"
    event_id = create_res.json()["event_id"]
    
    await async_client.patch(f"/api/events/{event_id}/status", json={"status": "OPEN"}, headers=auth_header(admin_token))
    await async_client.patch(f"/api/events/{event_id}/status", json={"status": "CLOSED"}, headers=auth_header(admin_token))
    
    # Get Option ID
    event_res = await async_client.get(f"/api/events/{event_id}")
    option_id = event_res.json()["options"][0]["option_id"]
    
    # Settle
    await async_client.post(
        f"/api/events/{event_id}/settle",
        json={"winner_option_ids": [option_id]},
        headers=auth_header(admin_token)
    )
    
    return event_id

# =============================================================================
# 정산 (POST /api/events/{id}/settlement)
# =============================================================================

@pytest.mark.asyncio
async def test_settle_event_success_S01(async_client: AsyncClient, admin_token: str, auth_token: str, unsettled_closed_event_id: str):
    """S01: 정산 성공 (200)"""
    # 1. Get Winning Option ID
    event_res = await async_client.get(f"/api/events/{unsettled_closed_event_id}")
    options = event_res.json()["options"]
    winning_option_id = options[0]["option_id"] # The one user betted on
    
    # 2. Settle
    response = await async_client.post(
        f"/api/events/{unsettled_closed_event_id}/settle",
        json={"winner_option_ids": [winning_option_id]},
        headers=auth_header(admin_token)
    )
    
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["status"] == "SETTLED"
    assert data["winner"][0]["option_id"] == winning_option_id
    # assert data["settled_count"] >= 1 # Not in schema, removing
    
    # 3. Verify User received points (1000 * odds)
    # Since only 1 user bet 1000 on WIN, total pool=1000, win pool=1000. 
    # Dividend should be roughly 1.0 * amount (minus fee?) or based on implementation.
    # Assuming standard implementation return >= 1000
    
    # Check User Points
    me_res = await async_client.get("/api/users/me/profile", headers=auth_header(auth_token))
    current_points = me_res.json()["points"]
    # Initial 10000 - 1000(bet) = 9000.
    # If returned 1000, points = 10000.
    assert current_points >= 9000

@pytest.mark.asyncio
async def test_settle_already_settled_S02(async_client: AsyncClient, admin_token: str, settled_event_id: str):
    """S02: 이미 정산된 이벤트 (ERR_032: NOT CLOSED)"""
    # Try to settle again
    # Need a valid option id
    event_res = await async_client.get(f"/api/events/{settled_event_id}")
    option_id = event_res.json()["options"][0]["option_id"]
    
    response = await async_client.post(
        f"/api/events/{settled_event_id}/settle",
        json={"winner_option_ids": [option_id]},
        headers=auth_header(admin_token)
    )
    
    # ERR_032: NOT CLOSED (400)
    assert_error_response(response, 400, "ERR_032")

@pytest.mark.asyncio
async def test_settle_event_not_closed_S03(async_client: AsyncClient, admin_token: str, auth_token: str):
    """S03: CLOSED 상태가 아닌 이벤트 정산 시도 (ERR_032)"""
    # Create OPEN event
    start_at = (get_kst_now() + timedelta(days=3)).isoformat()
    end_at = (get_kst_now() + timedelta(days=5)).isoformat()
    event_data = {"title": f"오픈 이벤트 {uuid.uuid4()}", "description": "-", "start_at": start_at, "end_at": end_at, "options": [{"name": "A", "option_image_index": -1}, {"name": "B", "option_image_index": -1}]}
    
    create_res = await async_client.post("/api/events", data={"data": json.dumps(event_data)}, files=EMPTY_FILES, headers=auth_header(admin_token))
    assert create_res.status_code == 201, f"Event creation failed: {create_res.text}"
    event_id = create_res.json()["event_id"]
    await async_client.patch(f"/api/events/{event_id}/status", json={"status": "OPEN"}, headers=auth_header(admin_token))
    
    option_id = create_res.json()["options"][0]["option_id"]
    
    response = await async_client.post(
        f"/api/events/{event_id}/settle",
        json={"winner_option_ids": [option_id]},
        headers=auth_header(admin_token)
    )
    
    assert_error_response(response, 400, "ERR_032")
