"""
좋아요 기능 테스트 (L01-L07)
- POST /api/events/{event_id}/likes
- DELETE /api/events/{event_id}/likes
- GET /api/events/{event_id} (좋아요 정보 포함)
- GET /api/events?liked=true (좋아요 필터)
"""
from __future__ import annotations

import pytest
from httpx import AsyncClient
from datetime import timedelta
import json
import uuid
from snu_toto.tests.conftest import auth_header, assert_error_response
from snu_toto.app.core.date_utils import get_kst_now

# =============================================================================
# 이벤트 생성 헬퍼 (multipart/form-data)
# =============================================================================
# test_events.py와 동일하게 맞춤
EMPTY_FILES = {"ignore_me": ("ignore.txt", b"", "text/plain")}


def multipart_headers(token: str) -> dict:
    """multipart 요청용 헤더 (Content-Type 제외)"""
    return {"Authorization": f"Bearer {token}"}
# end def


@pytest.fixture
async def ready_event_id(async_client: AsyncClient, admin_token: str) -> str:
    """READY 상태의 이벤트 생성 후 ID 반환"""
    start_at = (get_kst_now() + timedelta(days=3)).isoformat()
    end_at = (get_kst_now() + timedelta(days=5)).isoformat()
    
    event_data = {
        "title": f"좋아요 테스트 이벤트 {uuid.uuid4()}",
        "description": "좋아요 테스트용",
        "start_at": start_at,
        "end_at": end_at,
        "options": [
            {"name": "옵션A", "option_image_index": -1},
            {"name": "옵션B", "option_image_index": -1}
        ],
        "images": []
    }
    
    create_res = await async_client.post(
        "/api/events",
        data={"data": json.dumps(event_data)},
        files=EMPTY_FILES,
        headers=multipart_headers(admin_token)
    )
    return create_res.json()["event_id"]
# end def


@pytest.fixture
async def open_event_id(async_client: AsyncClient, admin_token: str) -> str:
    """OPEN 상태의 이벤트 생성 후 ID 반환"""
    start_at = (get_kst_now() + timedelta(days=3)).isoformat()
    end_at = (get_kst_now() + timedelta(days=5)).isoformat()
    
    event_data = {
        "title": f"좋아요 테스트 OPEN 이벤트 {uuid.uuid4()}",
        "description": "좋아요 테스트용 OPEN",
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
        headers=multipart_headers(admin_token)
    )
    event_id = create_res.json()["event_id"]
    
    # 2. Update to OPEN
    await async_client.patch(
        f"/api/events/{event_id}/status",
        json={"status": "OPEN"},
        headers=auth_header(admin_token)
    )
    return event_id
# end def


# =============================================================================
# L01: 좋아요 추가 성공
# =============================================================================
@pytest.mark.asyncio
async def test_add_like_success_L01(async_client: AsyncClient, auth_token: str, open_event_id: str):
    """L01: 좋아요 추가 성공 (201 Created)"""
    response = await async_client.post(
        f"/api/events/{open_event_id}/likes",
        headers=auth_header(auth_token)
    )
    
    assert response.status_code == 201
    data = response.json()
    assert "like_id" in data
    assert data["event_id"] == open_event_id
    assert "user_id" in data
    assert "created_at" in data
# end def


# =============================================================================
# L02: 중복 좋아요
# =============================================================================
@pytest.mark.asyncio
async def test_add_like_duplicate_L02(async_client: AsyncClient, auth_token: str, open_event_id: str):
    """L02: 중복 좋아요 (ERR_052)"""
    # 1. 첫 번째 좋아요
    await async_client.post(
        f"/api/events/{open_event_id}/likes",
        headers=auth_header(auth_token)
    )
    
    # 2. 두 번째 좋아요 시도 → 에러
    response = await async_client.post(
        f"/api/events/{open_event_id}/likes",
        headers=auth_header(auth_token)
    )
    
    assert_error_response(response, 409, "ERR_052")
# end def


# =============================================================================
# L03: 좋아요 취소 성공
# =============================================================================
@pytest.mark.asyncio
async def test_remove_like_success_L03(async_client: AsyncClient, auth_token: str, open_event_id: str):
    """L03: 좋아요 취소 성공 (200 OK)"""
    # 1. 좋아요 추가
    await async_client.post(
        f"/api/events/{open_event_id}/likes",
        headers=auth_header(auth_token)
    )
    
    # 2. 좋아요 취소
    response = await async_client.delete(
        f"/api/events/{open_event_id}/likes",
        headers=auth_header(auth_token)
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["message"] == "좋아요가 취소되었습니다."
    assert data["event_id"] == open_event_id
# end def


# =============================================================================
# L04: 좋아요 안한 상태에서 취소
# =============================================================================
@pytest.mark.asyncio
async def test_remove_like_not_found_L04(async_client: AsyncClient, auth_token: str, open_event_id: str):
    """L04: 좋아요 안한 상태에서 취소 (ERR_053)"""
    response = await async_client.delete(
        f"/api/events/{open_event_id}/likes",
        headers=auth_header(auth_token)
    )
    
    assert_error_response(response, 404, "ERR_053")
# end def


# =============================================================================
# L05: 없는 이벤트에 좋아요
# =============================================================================
@pytest.mark.asyncio
async def test_add_like_event_not_found_L05(async_client: AsyncClient, auth_token: str):
    """L05: 없는 이벤트에 좋아요 (ERR_009)"""
    fake_event_id = str(uuid.uuid4())
    
    response = await async_client.post(
        f"/api/events/{fake_event_id}/likes",
        headers=auth_header(auth_token)
    )
    
    assert_error_response(response, 404, "ERR_009")
# end def


# =============================================================================
# L06: 이벤트 상세에 좋아요 정보 포함
# =============================================================================
@pytest.mark.asyncio
async def test_event_detail_includes_like_info_L06(async_client: AsyncClient, auth_token: str, open_event_id: str):
    """L06: 이벤트 상세 조회 시 like_count, is_liked 포함"""
    # 1. 좋아요 추가
    await async_client.post(
        f"/api/events/{open_event_id}/likes",
        headers=auth_header(auth_token)
    )
    
    # 2. 이벤트 상세 조회 (로그인 상태)
    response = await async_client.get(
        f"/api/events/{open_event_id}",
        headers=auth_header(auth_token)
    )
    
    assert response.status_code == 200
    data = response.json()
    assert "like_count" in data
    assert data["like_count"] >= 1
    assert "is_liked" in data
    assert data["is_liked"] is True
    
    # 3. 비로그인 상태에서 조회
    response_no_auth = await async_client.get(f"/api/events/{open_event_id}")
    data_no_auth = response_no_auth.json()
    assert "like_count" in data_no_auth
    assert data_no_auth["is_liked"] is None  # 비로그인 시 null
# end def


# =============================================================================
# L07: 좋아요한 이벤트 필터링
# =============================================================================
@pytest.mark.asyncio
async def test_event_list_liked_filter_L07(async_client: AsyncClient, auth_token: str, admin_token: str):
    """L07: 좋아요한 이벤트만 필터링 (GET /api/events?liked=true)"""
    start_at = (get_kst_now() + timedelta(days=3)).isoformat()
    end_at = (get_kst_now() + timedelta(days=5)).isoformat()
    
    # 1. 이벤트 2개 생성
    event_ids = []
    for i in range(2):
        event_data = {
            "title": f"필터 테스트 이벤트 {i} {uuid.uuid4()}",
            "description": "필터 테스트",
            "start_at": start_at,
            "end_at": end_at,
            "options": [
                {"name": "옵션A", "option_image_index": -1},
                {"name": "옵션B", "option_image_index": -1}
            ],
            "images": []
        }
        
        create_res = await async_client.post(
            "/api/events",
            data={"data": json.dumps(event_data)},
            files=EMPTY_FILES,
            headers=multipart_headers(admin_token)
        )
        event_id = create_res.json()["event_id"]
        
        # OPEN 상태로 변경
        await async_client.patch(
            f"/api/events/{event_id}/status",
            json={"status": "OPEN"},
            headers=auth_header(admin_token)
        )
        event_ids.append(event_id)
    # end for
    
    # 2. 첫 번째 이벤트만 좋아요
    await async_client.post(
        f"/api/events/{event_ids[0]}/likes",
        headers=auth_header(auth_token)
    )
    
    # 3. 좋아요한 이벤트만 조회
    response = await async_client.get(
        "/api/events?liked=true",
        headers=auth_header(auth_token)
    )
    
    assert response.status_code == 200
    data = response.json()
    
    # 좋아요한 이벤트만 포함되어 있는지 확인
    event_ids_in_response = [e["event_id"] for e in data.get("events", [])]
    assert event_ids[0] in event_ids_in_response
    # 두 번째 이벤트는 좋아요 안했으므로 포함되지 않아야 함
    assert event_ids[1] not in event_ids_in_response
# end def
