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
from snu_toto.app.events.schemas import EventCreateRequest, EventCreateResponse, EventDetailResponse, EventListResponse, EventSettleRequest, EventSettleResponse, EventStatusUpdateRequest, WinnerOptionDetail
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

@event_router.get("/", status_code=200)
async def get_events(
    event_service: Annotated[EventServices, Depends()],
    status: EventStatus | None = Query(None),
    cursor: str | None = Query(None),
    limit: int = Query(10, ge=1, le=100)
) -> EventListResponse:
    """이벤트 목록 조회 API (커서 기반 페이지네이션)"""
    
    # limit 범위 검증
    if limit < 1 or limit > 100:
        raise OutOfRangeError()
    
    return await event_service.get_events_paginated(
        status=status,
        cursor=cursor,
        limit=limit
    )

@event_router.get("/{event_id}", status_code=200)
async def get_event_details(
    event_id: str,
    event_service: Annotated[EventServices, Depends()]
) -> EventDetailResponse:
    """이벤트 상세 조회 API"""
    event_details = await event_service.get_event_details(event_id)
    return event_details

@event_router.post("/{event_id}/settle", status_code=200)
async def settle_event(
    event_id: str,
    payload: EventSettleRequest,
    service: Annotated[EventServices, Depends(get_event_service)],
    admin: Annotated[User, Depends(get_current_admin_user)]
) -> EventSettleResponse:
    """이벤트를 정산"""

    event = await service.settle_event(event_id, payload.winner_option_ids)
    
    winners = [
        WinnerOptionDetail(option_id=opt.option_id, name=opt.name)
        for opt in event.options if opt.is_winner
    ]
    
    return EventSettleResponse(
        event_id=event.event_id,
        status=event.status,
        winner=winners
    )