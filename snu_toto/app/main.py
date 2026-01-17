import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from fastapi.exception_handlers import request_validation_exception_handler

from snu_toto.app.core.database import engine
from snu_toto.app.core.config import SETTINGS
from snu_toto.app.common.exceptions import SnutotoException, MissingRequiredFieldException, InvalidFormatException
from snu_toto.app.events.schedular import auto_update_event_status
from snu_toto.app.users import models as user_models
from snu_toto.app.events import models as event_models
from snu_toto.app.bets import models as bet_models


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 앱 시작 시
    task = asyncio.create_task(auto_update_event_status())

    yield

    # 앱 종료 시
    await engine.dispose()
    task.cancel()


app = FastAPI(
    title="SNU-TOTO API",
    description="이벤트 베팅 서비스",
    version="1.0.0",
    lifespan=lifespan,
    redirect_slashes=False
)

ORIGINS = [
    "https://d55bqrug1d7zs.cloudfront.net",  # 운영 환경
    "http://localhost:3000",                # React 로컬 기본값
    "http://localhost:5173",                # Vite 로컬 기본값
    "http://127.0.0.1:3000",
    "http://127.0.0.1:5173",
]

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# 라우터 등록 (라우터 파일이 구현되면 주석 해제)
from .auth.router import auth_router
from .users.router import users_router
from .events.router import event_router
from .bets.router import bet_router
from .admin.router import admin_router

app.include_router(auth_router, prefix="/api/auth", tags=["auth"])
app.include_router(users_router, prefix="/api/users", tags=["users"])
app.include_router(event_router, prefix="/api/events", tags=["events"])
app.include_router(bet_router, prefix="/api", tags=["bets"])
app.include_router(admin_router, prefix="/api/admin", tags=["admin"])

# 커스텀 예외 핸들러
@app.exception_handler(SnutotoException)
async def custom_exception_handler(request: Request, exc: SnutotoException):
    content = {
            "error_code": exc.error_code,
            "error_msg": exc.error_msg
        }
        
    # payload 안에 데이터(예: verification_token)가 있다면 병합
    if exc.payload:
        content.update(exc.payload)
        
    return JSONResponse(
        status_code=exc.status_code,
        content=content
    )
# 에러 형태 통일
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    for error in exc.errors():
        # 필수 필드 누락(ERR_001)
        if error["type"] == "missing":
            raise MissingRequiredFieldException()

        # 형식 및 길이 위반(ERR_002)
        if error["type"] in ["string_too_short", "string_too_long", "value_error", "email_type", "enum", "list_type", "string_type"]:
            raise InvalidFormatException()
        
    return await request_validation_exception_handler(request, exc)

@app.get("/")
async def health_check():
    return {"status": "ok", "message": "Welcome to SNU-TOTO API Server"}

