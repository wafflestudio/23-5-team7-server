
import pytest
from httpx import AsyncClient
import json
from datetime import timedelta
from snu_toto.tests.conftest import auth_header, assert_error_response
from snu_toto.app.core.date_utils import get_kst_now

# Helper to force multipart
def multipart_headers(token: str):
    # httpx handles boundary when files is passed, but we also need Auth
    return {"Authorization": f"Bearer {token}"}

# We need to pass 'files' to httpx to trigger multipart/form-data.
# Passing an empty dict might not trigger it if data is present.
# We pass a dummy file field that won't be used by the backend logic 
# (since image_files matches by name 'image_files' and this is 'ignore').
EMPTY_FILES = {"ignore_me": ("ignore.txt", b"", "text/plain")} 

# =============================================================================
# 1. 이벤트 생성 (POST /api/events)
# =============================================================================

@pytest.mark.asyncio
async def test_create_event_success_E01(async_client: AsyncClient, admin_token: str):
    """E01: 관리자 권한으로 이벤트 생성 성공 (옵션 2개 이상)"""
    # Given
    start_at = (get_kst_now() + timedelta(days=3)).isoformat()
    end_at = (get_kst_now() + timedelta(days=5)).isoformat()
    
    event_data = {
        "title": "테스트 이벤트입니다",
        "description": "설명",
        "start_at": start_at,
        "end_at": end_at,
        "options": [
            {"name": "옵션1", "option_image_index": -1}, # -1 means no image
            {"name": "옵션2", "option_image_index": -1}
        ],
        "images": []
    }

    # When
    response = await async_client.post(
        "/api/events",
        data={"data": json.dumps(event_data)},
        files=EMPTY_FILES,
        headers=auth_header(admin_token)
    )

    # Then
    assert response.status_code == 201
    data = response.json()
    assert data["title"] == event_data["title"]
    assert data["status"] == "READY"
    assert len(data["options"]) == 2
    # Value Verification
    option_names = [opt["name"] for opt in data["options"]]
    assert "옵션1" in option_names
    assert "옵션2" in option_names
    assert "event_id" in data

@pytest.mark.asyncio
async def test_create_event_success_E02(async_client: AsyncClient, admin_token: str):
    """E02: 옵션 3개로 생성 성공"""
    start_at = (get_kst_now() + timedelta(days=3)).isoformat()
    end_at = (get_kst_now() + timedelta(days=5)).isoformat()
    
    event_data = {
        "title": "3파전 이벤트 테스트",
        "start_at": start_at,
        "end_at": end_at,
        "options": [
            {"name": "A팀", "option_image_index": -1},
            {"name": "B팀", "option_image_index": -1},
            {"name": "C팀", "option_image_index": -1}
        ]
    }

    response = await async_client.post(
        "/api/events",
        data={"data": json.dumps(event_data)},
        files=EMPTY_FILES,
        headers=auth_header(admin_token)
    )

    assert response.status_code == 201
    data = response.json()
    assert len(data["options"]) == 3
    # Value Verification
    returned_names = [opt["name"] for opt in data["options"]]
    assert returned_names == ["A팀", "B팀", "C팀"] # Order preserved? Repo orders by `order` field which is set by index. So yes.

@pytest.mark.asyncio
async def test_create_event_duplicate_options_E03(async_client: AsyncClient, admin_token: str):
    """E03: 중복된 옵션 이름이 있는 경우 실패"""
    start_at = (get_kst_now() + timedelta(days=3)).isoformat()
    end_at = (get_kst_now() + timedelta(days=5)).isoformat()
    
    event_data = {
        "title": "중복 옵션 테스트",
        "start_at": start_at,
        "end_at": end_at,
        "options": [
            {"name": "같은이름", "option_image_index": -1},
            {"name": "같은이름", "option_image_index": -1}
        ]
    }

    response = await async_client.post(
        "/api/events",
        data={"data": json.dumps(event_data)},
        files=EMPTY_FILES,
        headers=auth_header(admin_token)
    )

    assert_error_response(response, 409, "ERR_028")

@pytest.mark.asyncio
async def test_create_event_invalid_dates_E07(async_client: AsyncClient, admin_token: str):
    """E07: 시작 시간이 현재보다 과거이거나, 종료 시간이 시작 시간보다 빠른 경우"""
    # Case 1: Start time in past
    past_start = (get_kst_now() - timedelta(hours=1)).isoformat()
    future_end = (get_kst_now() + timedelta(hours=1)).isoformat()
    
    event_data = {
        "title": "과거 시작 이벤트",
        "start_at": past_start,
        "end_at": future_end,
        "options": [{"name": "A", "option_image_index": -1}, {"name": "B", "option_image_index": -1}]
    }

    response = await async_client.post(
        "/api/events",
        data={"data": json.dumps(event_data)},
        files=EMPTY_FILES,
        headers=auth_header(admin_token)
    )
    assert_error_response(response, 400, "ERR_023") # InvalidDateError

    # Case 2: End time before Start time
    start = (get_kst_now() + timedelta(days=3)).isoformat()
    end_before_start = (get_kst_now() + timedelta(days=2)).isoformat()
    
    event_data["start_at"] = start
    event_data["end_at"] = end_before_start
    
    response = await async_client.post(
        "/api/events",
        data={"data": json.dumps(event_data)},
        files=EMPTY_FILES,
        headers=auth_header(admin_token)
    )
    assert_error_response(response, 400, "ERR_023")

@pytest.mark.asyncio
async def test_create_event_option_count_E08_E09(async_client: AsyncClient, admin_token: str):
    """E08, E09: 옵션 개수 제한 (2개 미만, 10개 초과)"""
    start_at = (get_kst_now() + timedelta(days=3)).isoformat()
    end_at = (get_kst_now() + timedelta(days=5)).isoformat()
    
    # Less than 2
    event_data = {
        "title": "옵션 부족",
        "start_at": start_at,
        "end_at": end_at,
        "options": [{"name": "하나뿐인옵션", "option_image_index": -1}]
    }
    response = await async_client.post(
        "/api/events",
        data={"data": json.dumps(event_data)},
        files=EMPTY_FILES,
        headers=auth_header(admin_token)
    )
    assert_error_response(response, 400, "ERR_024") # InvalidOptionCountError

    # More than 10
    event_data["options"] = [{"name": f"옵션{i}", "option_image_index": -1} for i in range(11)]
    response = await async_client.post(
        "/api/events",
        data={"data": json.dumps(event_data)},
        files=EMPTY_FILES,
        headers=auth_header(admin_token)
    )
    assert_error_response(response, 400, "ERR_024")

'''
@pytest.mark.asyncio
async def test_create_event_non_admin_E13(async_client: AsyncClient, auth_token: str):
    """E13 (Partial): 일반 유저가 이벤트 생성 시도 -> 403 Forbidden"""
    start_at = (get_kst_now() + timedelta(hours=1)).isoformat()
    end_at = (get_kst_now() + timedelta(days=1)).isoformat()
    
    event_data = {
        "title": "해킹 시도",
        "start_at": start_at,
        "end_at": end_at,
        "options": [{"name": "A", "option_image_index": -1}, {"name": "B", "option_image_index": -1}]
    }

    response = await async_client.post(
        "/api/events",
        data={"data": json.dumps(event_data)},
        files=EMPTY_FILES,
        headers=auth_header(auth_token)
    )
    # 일반 유저는 ForbiddenException (ERR_030 or similar standard 403)
    # Check dependencies.py for get_current_admin_user implementation
    assert response.status_code == 403
'''

# =============================================================================
# 2. 상태 변경 (PATCH /api/events/{id}/status)
# =============================================================================

@pytest.fixture
async def ready_event_id(async_client: AsyncClient, admin_token: str) -> str:
    """READY 상태의 이벤트를 생성하고 ID 반환"""
    start_at = (get_kst_now() + timedelta(days=3)).isoformat()
    end_at = (get_kst_now() + timedelta(days=5)).isoformat()
    event_data = {
        "title": "상태 변경 테스트용",
        "start_at": start_at,
        "end_at": end_at,
        "options": [{"name": "A", "option_image_index": -1}, {"name": "B", "option_image_index": -1}]
    }
    res = await async_client.post(
        "/api/events",
        data={"data": json.dumps(event_data)},
        files=EMPTY_FILES,
        headers=auth_header(admin_token)
    )
    return res.json()["event_id"]

@pytest.mark.asyncio
async def test_update_status_flow_E10_E11(async_client: AsyncClient, admin_token: str, ready_event_id: str):
    """E10, E11: READY -> OPEN -> CLOSED 정상 흐름"""
    
    # 1. READY -> OPEN
    response = await async_client.patch(
        f"/api/events/{ready_event_id}/status",
        json={"status": "OPEN"},
        headers=auth_header(admin_token)
    )
    assert response.status_code == 200
    
    # Verify status
    get_res = await async_client.get(f"/api/events/{ready_event_id}")
    assert get_res.json()["status"] == "OPEN"

    # 2. OPEN -> CLOSED
    response = await async_client.patch(
        f"/api/events/{ready_event_id}/status",
        json={"status": "CLOSED"},
        headers=auth_header(admin_token)
    )
    assert response.status_code == 200
    
    # Verify status
    get_res = await async_client.get(f"/api/events/{ready_event_id}")
    assert get_res.json()["status"] == "CLOSED"

@pytest.mark.asyncio
async def test_update_status_invalid_transition_E12(async_client: AsyncClient, admin_token: str, ready_event_id: str):
    """E12: 유효하지 않은 상태 변경 (READY -> CLOSED 바로 이동 불가 등)"""
    # READY -> CLOSED (Not allowed usually, depends on logic but typically sequential)
    # Assuming logic allows READY->OPEN->CLOSED->SETTLED
    
    # Try READY -> SETTLED directly
    response = await async_client.patch(
        f"/api/events/{ready_event_id}/status",
        json={"status": "SETTLED"},
        headers=auth_header(admin_token)
    )
    assert_error_response(response, 400, "ERR_029") # InvalidStatusTransitionError

@pytest.mark.asyncio
async def test_update_status_non_admin_E13(async_client: AsyncClient, auth_token: str, ready_event_id: str):
    """E13: 비관리자가 상태 변경 시도"""
    response = await async_client.patch(
        f"/api/events/{ready_event_id}/status",
        json={"status": "OPEN"},
        headers=auth_header(auth_token)
    )
    assert response.status_code == 403

# =============================================================================
# 3. 이벤트 조회 (GET /api/events) - Basic
# =============================================================================

@pytest.mark.asyncio
async def test_get_events_list_E16(async_client: AsyncClient, ready_event_id: str):
    """E16: 이벤트 목록 조회 성공"""
    response = await async_client.get("/api/events")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, dict)
    assert len(data) >= 1
    # Check if created event is in list
    assert any(e[0]["event_id"] == ready_event_id for e in data.values())

@pytest.mark.asyncio
async def test_get_event_detail_E18(async_client: AsyncClient, ready_event_id: str):
    """E18: 이벤트 상세 조회 성공"""
    response = await async_client.get(f"/api/events/{ready_event_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["event_id"] == ready_event_id
    assert "options" in data
    assert len(data["options"]) == 2

@pytest.mark.asyncio
async def test_get_event_detail_not_found_E19(async_client: AsyncClient):
    """E19: 존재하지 않는 이벤트 조회"""
    response = await async_client.get("/api/events/non_existent_id")
    assert response.status_code == 404
