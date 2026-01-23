"""
베팅(Bets) 및 관리자(Admin) 기능 테스트
"""
import pytest
from httpx import AsyncClient
import json
from datetime import datetime, timedelta
from snu_toto.tests.conftest import auth_header, assert_error_response

# Helper to force multipart for event creation
EMPTY_FILES: dict = {"ignore_me": ("ignore.txt", b"", "text/plain")}


# =============================================================================
# Fixtures: OPEN 상태 이벤트 생성
# =============================================================================
@pytest.fixture
async def open_event_data(async_client: AsyncClient, admin_token: str) -> dict:
    """OPEN 상태의 이벤트 생성 후 {event_id, option_id} 반환"""
    # 1. Create Event
    start_at: str = (datetime.now() + timedelta(hours=1)).isoformat()
    end_at: str = (datetime.now() + timedelta(days=1)).isoformat()
    event_data: dict = {
        "title": "베팅 테스트용 이벤트",
        "start_at": start_at,
        "end_at": end_at,
        "options": [
            {"name": "Win", "option_image_index": -1},
            {"name": "Lose", "option_image_index": -1}
        ],
        "images": []
    }

    res = await async_client.post(
        "/api/events",
        data={"data": json.dumps(event_data)},
        files=EMPTY_FILES,
        headers=auth_header(admin_token)
    )
    assert res.status_code == 201
    event_id: str = res.json()["event_id"]
    option_id: str = res.json()["options"][0]["option_id"]

    # 2. Update status to OPEN
    await async_client.patch(
        f"/api/events/{event_id}/status",
        json={"status": "OPEN"},
        headers=auth_header(admin_token)
    )

    return {"event_id": event_id, "option_id": option_id}
# end def


@pytest.fixture
async def ready_event_data(async_client: AsyncClient, admin_token: str) -> dict:
    """READY 상태의 이벤트 생성 후 {event_id, option_id} 반환"""
    start_at: str = (datetime.now() + timedelta(hours=1)).isoformat()
    end_at: str = (datetime.now() + timedelta(days=1)).isoformat()
    event_data: dict = {
        "title": "READY 상태 이벤트",
        "start_at": start_at,
        "end_at": end_at,
        "options": [
            {"name": "Option A", "option_image_index": -1},
            {"name": "Option B", "option_image_index": -1}
        ],
        "images": []
    }

    res = await async_client.post(
        "/api/events",
        data={"data": json.dumps(event_data)},
        files=EMPTY_FILES,
        headers=auth_header(admin_token)
    )
    assert res.status_code == 201
    return {
        "event_id": res.json()["event_id"],
        "option_id": res.json()["options"][0]["option_id"]
    }
# end def


# =============================================================================
# 1. 베팅 생성 (POST /api/events/{event_id}/bets)
# =============================================================================
@pytest.mark.asyncio
async def test_create_bet_success_B01(
    async_client: AsyncClient,
    auth_token: str,
    open_event_data: dict
) -> None:
    """B01: 베팅 성공 (잔액 충분, OPEN 상태)"""
    # Given
    event_id: str = open_event_data["event_id"]
    option_id: str = open_event_data["option_id"]
    bet_data: dict = {
        "option_id": option_id,
        "bet_amount": 1000
    }

    # When
    response = await async_client.post(
        f"/api/events/{event_id}/bets",
        json=bet_data,
        headers=auth_header(auth_token)
    )

    # Then
    assert response.status_code == 201
    data: dict = response.json()
    assert data["bet_amount"] == 1000
    assert data["status"] == "PENDING"
    assert "bet_id" in data
    assert data["option_id"] == option_id
# end def


@pytest.mark.asyncio
async def test_create_bet_insufficient_balance_B02(
    async_client: AsyncClient,
    auth_token: str,
    open_event_data: dict
) -> None:
    """B02: 잔액 부족 (보유 10000, 베팅 20000)"""
    # Given
    event_id: str = open_event_data["event_id"]
    option_id: str = open_event_data["option_id"]
    bet_data: dict = {
        "option_id": option_id,
        "bet_amount": 20000  # 초기 포인트 10000보다 큼
    }

    # When
    response = await async_client.post(
        f"/api/events/{event_id}/bets",
        json=bet_data,
        headers=auth_header(auth_token)
    )

    # Then
    assert_error_response(response, 400, "ERR_038")
# end def


@pytest.mark.asyncio
async def test_create_bet_duplicate_B03(
    async_client: AsyncClient,
    auth_token: str,
    open_event_data: dict
) -> None:
    """B03: 중복 베팅 (이미 베팅한 이벤트에 다시 베팅)"""
    # Given
    event_id: str = open_event_data["event_id"]
    option_id: str = open_event_data["option_id"]

    # 1st Bet
    await async_client.post(
        f"/api/events/{event_id}/bets",
        json={"option_id": option_id, "bet_amount": 100},
        headers=auth_header(auth_token)
    )

    # When: 2nd Bet
    response = await async_client.post(
        f"/api/events/{event_id}/bets",
        json={"option_id": option_id, "bet_amount": 100},
        headers=auth_header(auth_token)
    )

    # Then
    assert_error_response(response, 409, "ERR_041")
# end def


@pytest.mark.asyncio
async def test_create_bet_not_open_B04(
    async_client: AsyncClient,
    auth_token: str,
    ready_event_data: dict
) -> None:
    """B04: OPEN 상태가 아닌 이벤트(READY)에 베팅"""
    # Given
    event_id: str = ready_event_data["event_id"]
    option_id: str = ready_event_data["option_id"]

    # When
    response = await async_client.post(
        f"/api/events/{event_id}/bets",
        json={"option_id": option_id, "bet_amount": 100},
        headers=auth_header(auth_token)
    )

    # Then
    assert_error_response(response, 409, "ERR_040")
# end def


@pytest.mark.asyncio
async def test_create_bet_event_not_found_B05(
    async_client: AsyncClient,
    auth_token: str
) -> None:
    """B05: 존재하지 않는 이벤트에 베팅"""
    # When
    response = await async_client.post(
        "/api/events/non_existent_event_id/bets",
        json={"option_id": "fake_option", "bet_amount": 100},
        headers=auth_header(auth_token)
    )

    # Then
    assert_error_response(response, 404, "ERR_009")
# end def


@pytest.mark.asyncio
async def test_create_bet_option_not_found_B06(
    async_client: AsyncClient,
    auth_token: str,
    open_event_data: dict
) -> None:
    """B06: 존재하지 않는 옵션에 베팅"""
    # Given
    event_id: str = open_event_data["event_id"]

    # When
    response = await async_client.post(
        f"/api/events/{event_id}/bets",
        json={"option_id": "non_existent_option", "bet_amount": 100},
        headers=auth_header(auth_token)
    )

    # Then
    assert_error_response(response, 404, "ERR_039")
# end def


# =============================================================================
# 2. 관리자용 베팅 조회 (GET /api/admin/events/{event_id}/bets)
# =============================================================================
@pytest.mark.asyncio
async def test_admin_get_event_bets_success(
    async_client: AsyncClient,
    admin_token: str,
    auth_token: str,
    open_event_data: dict
) -> None:
    """관리자용 베팅 조회 성공"""
    # Given: 유저가 베팅 생성
    event_id: str = open_event_data["event_id"]
    option_id: str = open_event_data["option_id"]

    await async_client.post(
        f"/api/events/{event_id}/bets",
        json={"option_id": option_id, "bet_amount": 500},
        headers=auth_header(auth_token)
    )

    # When: 관리자가 조회
    response = await async_client.get(
        f"/api/admin/events/{event_id}/bets",
        headers=auth_header(admin_token)
    )

    # Then
    assert response.status_code == 200
    data: dict = response.json()

    # 이벤트 정보 검증
    assert data["event_info"]["event_id"] == event_id
    assert data["event_info"]["total_bet_count"] == 1
    assert data["event_info"]["total_bet_amount"] == 500

    # 베팅 목록 검증
    assert len(data["bets"]) == 1
    assert data["bets"][0]["amount"] == 500
    assert data["bets"][0]["selected_option"]["option_id"] == option_id

    # 페이지네이션 검증
    assert data["pagination"]["total"] == 1
    assert data["pagination"]["current_page"] == 1
# end def


@pytest.mark.asyncio
async def test_admin_get_event_bets_forbidden(
    async_client: AsyncClient,
    auth_token: str,
    open_event_data: dict
) -> None:
    """비관리자가 관리자용 API 접근 시 403"""
    # Given
    event_id: str = open_event_data["event_id"]

    # When: 일반 유저가 접근
    response = await async_client.get(
        f"/api/admin/events/{event_id}/bets",
        headers=auth_header(auth_token)
    )

    # Then
    assert response.status_code == 403
# end def


@pytest.mark.asyncio
async def test_admin_get_event_bets_not_found(
    async_client: AsyncClient,
    admin_token: str
) -> None:
    """존재하지 않는 이벤트 조회 시 404"""
    # When
    response = await async_client.get(
        "/api/admin/events/non_existent_event/bets",
        headers=auth_header(admin_token)
    )

    # Then
    assert_error_response(response, 404, "ERR_009")
# end def


@pytest.mark.asyncio
async def test_admin_get_event_bets_pagination(
    async_client: AsyncClient,
    admin_token: str,
    open_event_data: dict
) -> None:
    """페이지네이션 파라미터 동작 검증"""
    # Given
    event_id: str = open_event_data["event_id"]

    # When: page와 limit 파라미터 사용
    response = await async_client.get(
        f"/api/admin/events/{event_id}/bets?page=1&limit=5",
        headers=auth_header(admin_token)
    )

    # Then
    assert response.status_code == 200
    data: dict = response.json()
    assert data["pagination"]["limit"] == 5
    assert data["pagination"]["current_page"] == 1
# end def


# =============================================================================
# 3. WebSocket 실시간 배당률 (WS /api/events/ws/{event_id})
# =============================================================================
@pytest.mark.asyncio
async def test_websocket_initial_odds(
    async_client: AsyncClient,
    admin_token: str,
    open_event_data: dict
) -> None:
    """WebSocket 연결 시 초기 배당률 데이터 수신 확인"""
    # Given
    event_id: str = open_event_data["event_id"]

    # When: WebSocket 연결
    # Note: httpx는 WebSocket을 직접 지원하지 않으므로, 
    # 실제 테스트는 websockets 라이브러리 또는 Starlette TestClient를 사용해야 함.
    # 여기서는 HTTP fallback으로 이벤트 상세 조회를 통해 odds 필드 존재 여부만 확인
    response = await async_client.get(f"/api/events/{event_id}")

    # Then
    assert response.status_code == 200
    data: dict = response.json()
    for option in data["options"]:
        assert "odds" in option
    # end for
# end def


@pytest.mark.asyncio
async def test_websocket_event_not_found() -> None:
    """WebSocket: 존재하지 않는 이벤트 → 1008 종료 코드"""
    # Note: WebSocket 테스트는 별도 라이브러리(websockets, starlette.testclient)가 필요
    # 해당 테스트는 추후 WebSocket 테스트 환경 구축 시 활성화
    pytest.skip("WebSocket 테스트 환경 미구축 (websockets 라이브러리 필요)")
# end def
