"""
댓글 기능 테스트 (C01-C08)
- POST /api/events/{event_id}/comments
- GET /api/events/{event_id}/comments
- PATCH /api/comments/{comment_id}
- DELETE /api/comments/{comment_id}
"""
from __future__ import annotations

import pytest
from httpx import AsyncClient
from datetime import timedelta
import uuid
from snu_toto.tests.conftest import auth_header, assert_error_response
from snu_toto.app.core.date_utils import get_kst_now
# end imports


# =============================================================================
# 이벤트 생성 헬퍼 (multipart/form-data)
# =============================================================================
EMPTY_FILES = {"ignore_me": ("ignore.txt", b"", "text/plain")}


def multipart_headers(token: str) -> dict[str, str]:
    """multipart 요청용 헤더 (Authorization만)"""
    return {"Authorization": f"Bearer {token}"}
# end def


@pytest.fixture
async def open_event_id(async_client: AsyncClient, admin_token: str) -> str:
    """OPEN 상태의 이벤트 생성 후 ID 반환"""
    start_at = (get_kst_now() + timedelta(days=2) + timedelta(hours=1)).isoformat()
    end_at = (get_kst_now() + timedelta(days=3) + timedelta(hours=2)).isoformat()
    
    event_data = {
        "title": f"댓글 테스트 이벤트 {uuid.uuid4()}",
        "description": "댓글 테스트용",
        "start_at": start_at,
        "end_at": end_at,
        "options": [
            {"name": "옵션A", "option_image_index": -1},
            {"name": "옵션B", "option_image_index": -1},
        ],
        "images": [],
    }
    
    import json
    response = await async_client.post(
        "/api/events",
        data={"data": json.dumps(event_data)},
        files=EMPTY_FILES,
        headers=multipart_headers(admin_token),
    )
    assert response.status_code == 201, f"이벤트 생성 실패: {response.text}"
    event_id = response.json()["event_id"]
    
    # OPEN 상태로 변경
    status_response = await async_client.patch(
        f"/api/events/{event_id}/status",
        json={"status": "OPEN"},
        headers=auth_header(admin_token),
    )
    assert status_response.status_code == 200, f"상태 변경 실패: {status_response.text}"
    
    return event_id
# end def


# =============================================================================
# C01: 댓글 작성 성공
# =============================================================================
@pytest.mark.asyncio
async def test_create_comment_success_C01(async_client: AsyncClient, auth_token: str, open_event_id: str):
    """C01: 댓글 작성 성공"""
    # Given
    comment_content = "테스트 댓글입니다!"
    
    # When
    response = await async_client.post(
        f"/api/events/{open_event_id}/comments",
        json={"content": comment_content},
        headers=auth_header(auth_token),
    )
    
    # Then
    assert response.status_code == 201
    data = response.json()
    assert data["content"] == comment_content
    assert data["event_id"] == open_event_id
    assert "comment_id" in data
    assert "nickname" in data
    assert "created_at" in data
# end def


# =============================================================================
# C02: 댓글 작성 - 빈 내용 (공백만)
# =============================================================================
@pytest.mark.asyncio
async def test_create_comment_empty_content_C02(async_client: AsyncClient, auth_token: str, open_event_id: str):
    """C02: 댓글 내용이 공백만으로 구성됨 → ERR_048"""
    # Given
    empty_content = "   "
    
    # When
    response = await async_client.post(
        f"/api/events/{open_event_id}/comments",
        json={"content": empty_content},
        headers=auth_header(auth_token),
    )
    
    # Then
    assert_error_response(response, 400, "ERR_048")
# end def


# =============================================================================
# C03: 댓글 작성 - 없는 이벤트
# =============================================================================
@pytest.mark.asyncio
async def test_create_comment_event_not_found_C03(async_client: AsyncClient, auth_token: str):
    """C03: 존재하지 않는 이벤트에 댓글 작성 → ERR_009"""
    # Given
    non_existent_event_id = "non-existent-event-id"
    
    # When
    response = await async_client.post(
        f"/api/events/{non_existent_event_id}/comments",
        json={"content": "테스트 댓글"},
        headers=auth_header(auth_token),
    )
    
    # Then
    assert_error_response(response, 404, "ERR_009")
# end def


# =============================================================================
# C04: 댓글 목록 조회
# =============================================================================
@pytest.mark.asyncio
async def test_get_comments_success_C04(async_client: AsyncClient, auth_token: str, open_event_id: str):
    """C04: 댓글 목록 조회 성공"""
    # Given - 댓글 2개 작성
    for i in range(2):
        await async_client.post(
            f"/api/events/{open_event_id}/comments",
            json={"content": f"댓글 {i+1}"},
            headers=auth_header(auth_token),
        )
    # end for
    
    # When
    response = await async_client.get(
        f"/api/events/{open_event_id}/comments",
    )
    
    # Then
    assert response.status_code == 200
    data = response.json()
    assert "comments" in data
    assert len(data["comments"]) >= 2
    assert "has_more" in data
    
    # 내용 검증
    contents = [c["content"] for c in data["comments"]]
    assert "댓글 1" in contents
    assert "댓글 2" in contents
# end def


# =============================================================================
# C05: 댓글 수정 성공
# =============================================================================
@pytest.mark.asyncio
async def test_update_comment_success_C05(async_client: AsyncClient, auth_token: str, open_event_id: str):
    """C05: 댓글 수정 성공"""
    # Given - 댓글 작성
    create_response = await async_client.post(
        f"/api/events/{open_event_id}/comments",
        json={"content": "원본 댓글"},
        headers=auth_header(auth_token),
    )
    comment_id = create_response.json()["comment_id"]
    
    # When
    updated_content = "수정된 댓글"
    response = await async_client.patch(
        f"/api/comments/{comment_id}",
        json={"content": updated_content},
        headers=auth_header(auth_token),
    )
    
    # Then
    assert response.status_code == 200
    data = response.json()
    assert data["content"] == updated_content
    assert data["updated_at"] is not None
# end def


# =============================================================================
# C06: 댓글 수정 - 본인 아님
# =============================================================================
@pytest.mark.asyncio
async def test_update_comment_not_owner_C06(async_client: AsyncClient, auth_token: str, admin_token: str, open_event_id: str):
    """C06: 다른 사람의 댓글 수정 시도 → ERR_050"""
    # Given - 일반 유저가 댓글 작성
    create_response = await async_client.post(
        f"/api/events/{open_event_id}/comments",
        json={"content": "일반 유저 댓글"},
        headers=auth_header(auth_token),
    )
    comment_id = create_response.json()["comment_id"]
    
    # When - 관리자가 수정 시도 (관리자도 수정은 못함, 삭제만 가능)
    response = await async_client.patch(
        f"/api/comments/{comment_id}",
        json={"content": "관리자가 수정 시도"},
        headers=auth_header(admin_token),
    )
    
    # Then
    assert_error_response(response, 403, "ERR_050")
# end def


# =============================================================================
# C07: 댓글 삭제 성공
# =============================================================================
@pytest.mark.asyncio
async def test_delete_comment_success_C07(async_client: AsyncClient, auth_token: str, open_event_id: str):
    """C07: 댓글 삭제 성공 (본인)"""
    # Given - 댓글 작성
    create_response = await async_client.post(
        f"/api/events/{open_event_id}/comments",
        json={"content": "삭제할 댓글"},
        headers=auth_header(auth_token),
    )
    comment_id = create_response.json()["comment_id"]
    
    # When
    response = await async_client.delete(
        f"/api/comments/{comment_id}",
        headers=auth_header(auth_token),
    )
    
    # Then
    assert response.status_code == 204
# end def


# =============================================================================
# C08: 댓글 삭제 - 관리자 권한
# =============================================================================
@pytest.mark.asyncio
async def test_delete_comment_by_admin_C08(async_client: AsyncClient, auth_token: str, admin_token: str, open_event_id: str):
    """C08: 관리자가 다른 유저의 댓글 삭제"""
    # Given - 일반 유저가 댓글 작성
    create_response = await async_client.post(
        f"/api/events/{open_event_id}/comments",
        json={"content": "관리자가 삭제할 댓글"},
        headers=auth_header(auth_token),
    )
    comment_id = create_response.json()["comment_id"]
    
    # When - 관리자가 삭제
    response = await async_client.delete(
        f"/api/comments/{comment_id}",
        headers=auth_header(admin_token),
    )
    
    # Then
    assert response.status_code == 204
# end def
