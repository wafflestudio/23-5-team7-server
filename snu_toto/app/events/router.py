from typing import Annotated, List
from fastapi import APIRouter, Depends, File, Form, Query, Request, UploadFile
from pydantic import ValidationError
from snu_toto.app.common.exceptions import InvalidFormatException, SnutotoException
from snu_toto.app.events.dependencies import get_event_service
from snu_toto.app.events.exceptions import InvalidContentTypeError, OutOfRangeError
from snu_toto.app.events.models import EventStatus
from snu_toto.app.events.utils import parse_event_data
from snu_toto.app.users.models import User
from snu_toto.app.events.services import EventServices
from snu_toto.app.events.schemas import EventCreateRequest, EventCreateResponse, EventDetailResponse, EventListResponse, EventStatusUpdateRequest
from snu_toto.app.auth.dependencies import get_current_admin_user, get_current_user

event_router = APIRouter()

@event_router.post("/", status_code=201)
async def create_event(
    request: Request,
    data: Annotated[str, Form(...)], # JSON 데이터 문자열
    image_files: List[UploadFile] = File(default=[]), # 이미지 파일 리스트
    service: EventServices = Depends(get_event_service),
    current_user: User = Depends(get_current_user)
) -> EventCreateResponse:
    """새로운 이벤트 생성"""
    
    # Content-Type 검증
    content_type = request.headers.get("Content-Type", "")
    if "multipart/form-data" not in content_type:
        raise InvalidContentTypeError()

    # JSON 문자열 파싱
    parsed_json = parse_event_data(data)

    try:
        event_in = EventCreateRequest.model_validate(parsed_json)
    except ValidationError as e:
        for error in e.errors():
            original_error = error.get("ctx", {}).get("error")
            
            if isinstance(original_error, SnutotoException):
                raise original_error
        
        # 일반적인 Pydantic 검증 에러(필수 필드 누락 등)는 InvalidFormatException으로 처리
        raise InvalidFormatException()

    return await service.create_event(
        creator_id=current_user.user_id,
        data=event_in,
        image_files=image_files
    )

@event_router.patch("/{event_id}/status", status_code=200)
async def update_event_status(
    event_id: str,
    payload: EventStatusUpdateRequest,
    service: EventServices = Depends(get_event_service),
    admin: User = Depends(get_current_admin_user) # 관리자 권한 체크
):
    await service.update_event_status(event_id, payload.status)
    return {"message": "상태가 성공적으로 변경되었습니다."}

@event_router.get("/", status_code=200, response_model=EventListResponse)
async def get_events(
    event_service: Annotated[EventServices, Depends()],
    status: EventStatus | None = Query(None, description="이벤트 상태 필터 (OPEN, CLOSED, SETTLED)"),
    cursor: str | None = Query(None, description="페이지네이션 커서 (Base64 encoded)"),
    limit: int = Query(10, ge=1, le=100, description="한 번에 가져올 이벤트 개수 (1-100)")
) -> EventListResponse:
    """이벤트 목록 조회 API (커서 페이지네이션, 마감 임박순)"""
    # limit 범위 검증
    if limit < 1 or limit > 100:
        raise OutOfRangeError()
    
    events, next_cursor, has_more = await event_service.get_events_paginated(
        status=status,
        cursor=cursor,
        limit=limit
    )
    
    return EventListResponse(
        events=events,
        next_cursor=next_cursor,
        has_more=has_more
    )

@event_router.get("/{event_id}", status_code=200)
async def get_event_details(
    event_id: str,
    event_service: Annotated[EventServices, Depends()]
) -> EventDetailResponse:
    """이벤트 상세 조회 API"""
    event_details = await event_service.get_event_details(event_id)
    return event_details