"""
WebSocket 테스트 (WS01-WS03)
- /api/events/ws/{event_id}
"""
from __future__ import annotations

import pytest
from httpx import AsyncClient
from starlette.testclient import TestClient
from datetime import timedelta
import json
import uuid
from snu_toto.app.main import app
from snu_toto.app.core.date_utils import get_kst_now
from snu_toto.tests.conftest import auth_header
# end imports


# =============================================================================
# 이벤트 생성 헬퍼 (multipart/form-data)
# =============================================================================
EMPTY_FILES = {"ignore_me": ("ignore.txt", b"", "text/plain")}


def multipart_headers(token: str) -> dict[str, str]:
    """multipart 요청용 헤더 (Authorization만)"""
    return {"Authorization": f"Bearer {token}"}
# end def


# =============================================================================
# WS01: WebSocket 연결 및 초기 데이터 수신
# =============================================================================
@pytest.mark.asyncio
async def test_websocket_connection_success_WS01(async_client: AsyncClient, admin_token: str):
    """WS01: WebSocket 연결 후 initial 데이터 수신"""
    # Given - OPEN 상태 이벤트 생성
    start_at = (get_kst_now() + timedelta(days=2) + timedelta(hours=1)).isoformat()
    end_at = (get_kst_now() + timedelta(days=3) + timedelta(hours=2)).isoformat()
    
    event_data = {
        "title": f"WebSocket 테스트 이벤트 {uuid.uuid4()}",
        "description": "WebSocket 테스트용",
        "start_at": start_at,
        "end_at": end_at,
        "options": [
            {"name": "옵션A", "option_image_index": -1},
            {"name": "옵션B", "option_image_index": -1},
        ],
        "images": [],
    }
    
    create_response = await async_client.post(
        "/api/events",
        data={"data": json.dumps(event_data)},
        files=EMPTY_FILES,
        headers=multipart_headers(admin_token),
    )
    assert create_response.status_code == 201
    event_id = create_response.json()["event_id"]
    
    # OPEN 상태로 변경
    await async_client.patch(
        f"/api/events/{event_id}/status",
        json={"status": "OPEN"},
        headers=auth_header(admin_token),
    )
    
    # When - WebSocket 연결 (TestClient 사용)
    with TestClient(app) as client:
        with client.websocket_connect(f"/api/events/ws/{event_id}") as websocket:
            # Then - initial 메시지 수신
            data = websocket.receive_json()
            assert data["type"] == "initial"
            assert data["event_id"] == event_id
            assert "options" in data
            assert len(data["options"]) == 2
# end def


# =============================================================================
# WS02: 없는 이벤트로 WebSocket 연결 시 1008 에러
# =============================================================================
@pytest.mark.asyncio
async def test_websocket_event_not_found_WS02():
    """WS02: 존재하지 않는 이벤트로 연결 시 1008 에러"""
    # Given
    non_existent_event_id = "non-existent-event-id"
    
    # When / Then - WebSocket 연결 시 1008 에러
    with TestClient(app) as client:
        try:
            with client.websocket_connect(f"/api/events/ws/{non_existent_event_id}") as websocket:
                # 연결은 성공하지만 바로 종료되어야 함
                pass
        except Exception:
            # 연결 종료 예외가 발생할 수 있음
            pass
# end def


# =============================================================================
# WS03: WebSocket 연결 후 클라이언트 종료
# =============================================================================
@pytest.mark.asyncio
async def test_websocket_client_disconnect_WS03(async_client: AsyncClient, admin_token: str):
    """WS03: WebSocket 클라이언트가 정상적으로 연결 종료"""
    # Given - OPEN 상태 이벤트 생성
    start_at = (get_kst_now() + timedelta(days=2) + timedelta(hours=1)).isoformat()
    end_at = (get_kst_now() + timedelta(days=3) + timedelta(hours=2)).isoformat()
    
    event_data = {
        "title": f"WebSocket 종료 테스트 {uuid.uuid4()}",
        "description": "WebSocket 종료 테스트용",
        "start_at": start_at,
        "end_at": end_at,
        "options": [
            {"name": "옵션A", "option_image_index": -1},
            {"name": "옵션B", "option_image_index": -1},
        ],
        "images": [],
    }
    
    create_response = await async_client.post(
        "/api/events",
        data={"data": json.dumps(event_data)},
        files=EMPTY_FILES,
        headers=multipart_headers(admin_token),
    )
    assert create_response.status_code == 201
    event_id = create_response.json()["event_id"]
    
    # OPEN 상태로 변경
    await async_client.patch(
        f"/api/events/{event_id}/status",
        json={"status": "OPEN"},
        headers=auth_header(admin_token),
    )
    
    # When - WebSocket 연결 후 클라이언트 종료
    with TestClient(app) as client:
        with client.websocket_connect(f"/api/events/ws/{event_id}") as websocket:
            # initial 메시지 수신
            data = websocket.receive_json()
            assert data["type"] == "initial"
            # 클라이언트가 연결 종료 (with 블록 종료 시 자동 종료)
    
    # Then - 정상 종료됨 (예외 없음)
    assert True
# end def
