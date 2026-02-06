"""
SNU Toto 테스트 공통 픽스처 및 헬퍼 함수
"""
from typing import AsyncGenerator
import asyncio

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import (
    create_async_engine,
    async_sessionmaker,
    AsyncSession,
)
from sqlalchemy.pool import StaticPool
from httpx import AsyncClient, ASGITransport
from unittest.mock import AsyncMock

import os

# 테스트 환경 변수 주입 (앱 임포트 전에 설정해야 함)
os.environ["ENV"] = "test"
os.environ.setdefault("DB_DIALECT", "mysql")
os.environ.setdefault("DB_DRIVER", "aiomysql")
os.environ.setdefault("DB_HOST", "localhost")
os.environ.setdefault("DB_PORT", "3306")
os.environ.setdefault("DB_USER", "unused_test_user")
os.environ.setdefault("DB_PASSWORD", "unused_test_password")
os.environ.setdefault("DB_DATABASE", "unused_test_db")
os.environ.setdefault("GOOGLE_CLIENT_ID", "dummy_client_id")
os.environ.setdefault("GOOGLE_CLIENT_SECRET", "dummy_client_secret")
os.environ.setdefault("GOOGLE_REDIRECT_URI", "http://localhost:8000/callback")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")
os.environ.setdefault("SMTP_HOST", "localhost")
os.environ.setdefault("SMTP_PORT", "25")
os.environ.setdefault("SMTP_USER", "user")
os.environ.setdefault("SMTP_PASSWORD", "pass")
os.environ.setdefault("ACCESS_TOKEN_SECRET", "access_secret")
os.environ.setdefault("REFRESH_TOKEN_SECRET", "refresh_secret")
os.environ.setdefault("S3_AWS_ACCESS_KEY_ID", "pass")
os.environ.setdefault("S3_AWS_SECRET_ACCESS_KEY", "pass")
os.environ.setdefault("S3_AWS_REGION", "pass")
os.environ.setdefault("S3_BUCKET_NAME", "pass")

from snu_toto.app.main import app
from snu_toto.app.core.database import Base, get_db_session


# =============================================================================
# 이벤트 루프 (세션 범위)
# =============================================================================
@pytest.fixture(scope="session")
def event_loop():
    """세션 범위의 이벤트 루프 생성"""
    policy = asyncio.get_event_loop_policy()
    loop = policy.new_event_loop()
    yield loop
    loop.close()

from sqlalchemy import event
from sqlalchemy.engine import Engine
from sqlite3 import Connection as SQLite3Connection

@event.listens_for(Engine, "connect")
def _set_sqlite_pragma(dbapi_connection, connection_record):
    if isinstance(dbapi_connection, SQLite3Connection) or hasattr(dbapi_connection, "create_function"):
        cursor = dbapi_connection.cursor()
        # Foreign Key 제약조건 활성화
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()
        
        # MySQL chracter_length 호환 함수 등록
        dbapi_connection.create_function("CHAR_LENGTH", 1, len)


# =============================================================================
# DB 엔진 / 세션 (테스트용 인메모리 SQLite)
# =============================================================================
@pytest_asyncio.fixture(scope="function")
async def db_engine():
    """비동기 SQLite 인메모리 DB 엔진"""
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        poolclass=StaticPool,
        connect_args={"check_same_thread": False},
    )

    # MySQL 전용 CheckConstraint 제거 (SQLite 호환성)
    from snu_toto.app.events.models import Event
    mysql_only_constraints = ["check_event_start_after_created"]
    
    original_constraints = list(Event.__table__.constraints)
    for constraint in original_constraints:
        if hasattr(constraint, "name") and constraint.name in mysql_only_constraints:
            Event.__table__.constraints.remove(constraint)
        # end if
    # end for

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    # end with

    try:
        yield engine
    finally:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
        # end with
        await engine.dispose()
    # end try
# end def


@pytest_asyncio.fixture(scope="function")
async def db_session(db_engine) -> AsyncGenerator[AsyncSession, None]:
    """비동기 DB 세션"""
    async_session_maker = async_sessionmaker(
        db_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async with async_session_maker() as session:
        yield session
        await session.rollback()


# =============================================================================
# HTTP 클라이언트
# =============================================================================
from unittest.mock import AsyncMock


class MockRedis:
    """테스트용 Redis Mock"""
    def __init__(self):
        self.data = {}
        self.sorted_sets = {}  # zadd용
    # end def
    
    async def exists(self, key):
        return key in self.data
    # end def
    
    async def get(self, key):
        return self.data.get(key)
    # end def
    
    async def setex(self, key, ttl, value):
        self.data[key] = value
    # end def
    
    async def delete(self, key):
        if key in self.data:
            del self.data[key]
        # end if
    # end def
    
    async def zadd(self, key, mapping):
        """Sorted set에 추가"""
        if key not in self.sorted_sets:
            self.sorted_sets[key] = {}
        # end if
        self.sorted_sets[key].update(mapping)
    # end def
    
    async def zrem(self, key, *members):
        """Sorted set에서 삭제"""
        if key in self.sorted_sets:
            for member in members:
                self.sorted_sets[key].pop(member, None)
            # end for
        # end if
    # end def
    
    async def zrangebyscore(self, key, min_score, max_score, withscores=False):
        """Score 범위로 조회"""
        if key not in self.sorted_sets:
            return []
        # end if
        items = self.sorted_sets[key]
        result = [(k, v) for k, v in items.items() if min_score <= v <= max_score]
        if withscores:
            return result
        # end if
        return [k for k, v in result]
    # end def
    
    async def close(self):
        pass
    # end def
# end class


@pytest_asyncio.fixture
async def async_client(db_session) -> AsyncGenerator[AsyncClient, None]:
    """비동기 HTTP 클라이언트 (의존성 오버라이드 포함)"""
    from snu_toto.app.auth.dependencies import get_redis
    
    async def override_get_db_session():
        yield db_session
    # end def
    
    async def override_get_redis():
        yield MockRedis()
    # end def

    app.dependency_overrides[get_db_session] = override_get_db_session
    app.dependency_overrides[get_redis] = override_get_redis

    transport = ASGITransport(app=app)
    async with AsyncClient(
        transport=transport, 
        base_url="http://test",
        follow_redirects=True
    ) as ac:
        yield ac
    
    app.dependency_overrides.clear()
# end def


# =============================================================================
# 유저 관련 픽스처
# =============================================================================
@pytest.fixture
def user_signup_data() -> dict:
    """회원가입 요청 데이터"""
    return {
        "email": "test@snu.ac.kr",
        "password": "password123",
        "nickname": "테스트유저",
    }


@pytest.fixture
def admin_signup_data() -> dict:
    """관리자 회원가입 데이터"""
    return {
        "email": "admin@snu.ac.kr",
        "password": "adminpass123",
        "nickname": "관리자",
    }


@pytest_asyncio.fixture
async def existing_user(async_client: AsyncClient, user_signup_data: dict) -> dict:
    """가입된 유저"""
    res = await async_client.post("/api/users", json=user_signup_data)
    return res.json()


@pytest_asyncio.fixture
async def auth_token(async_client: AsyncClient, user_signup_data: dict, db_session: AsyncSession) -> str:
    """로그인 후 access_token 반환 (인증 완료된 유저)"""
    # 가입
    await async_client.post("/api/users", json=user_signup_data)
    
    # 인증 완료 처리
    from snu_toto.app.users.models import User
    from sqlalchemy import select
    
    stmt = select(User).where(User.email == user_signup_data["email"])
    result = await db_session.execute(stmt)
    user = result.scalar_one()
    user.is_snu_verified = True
    await db_session.commit()
    
    # 로그인
    login_data = {
        "email": user_signup_data["email"],
        "password": user_signup_data["password"],
    }
    res = await async_client.post("/api/auth/login", json=login_data)
    return res.json().get("access_token", "")


@pytest_asyncio.fixture
async def admin_token(async_client: AsyncClient, admin_signup_data: dict, db_session: AsyncSession) -> str:
    """관리자 로그인 후 access_token 반환"""
    # 가입
    await async_client.post("/api/users", json=admin_signup_data)
    
    # 인증 및 관리자 권한 부여
    from snu_toto.app.users.models import User, UserRole
    from sqlalchemy import select
    
    stmt = select(User).where(User.email == admin_signup_data["email"])
    result = await db_session.execute(stmt)
    user = result.scalar_one()
    user.is_snu_verified = True
    user.role = UserRole.ADMIN
    await db_session.commit()
    
    # 로그인
    login_data = {
        "email": admin_signup_data["email"],
        "password": admin_signup_data["password"],
    }
    res = await async_client.post("/api/auth/login", json=login_data)
    return res.json().get("access_token", "")


@pytest_asyncio.fixture
async def another_user_token(async_client: AsyncClient) -> str:
    """다른 유저의 토큰"""
    signup_data = {
        "email": "another@snu.ac.kr",
        "password": "password1234",
        "nickname": "다른유저",
    }
    await async_client.post("/api/users", json=signup_data)
    
    login_data = {
        "email": signup_data["email"],
        "password": signup_data["password"],
    }
    res = await async_client.post("/api/auth/login", json=login_data)
    return res.json().get("access_token", "")


# =============================================================================
# 이벤트 관련 픽스처
# =============================================================================
@pytest.fixture
def event_create_data() -> dict:
    """이벤트 생성 요청 데이터"""
    return {
        "title": "공대 vs 자연대 축구",
        "description": "관악의 주인 결정전",
        "end_at": "2026-12-31T18:00:00",
        "options": [
            {"name": "공대 승", "order": 0},
            {"name": "자연대 승", "order": 1},
            {"name": "무승부", "order": 2},
        ],
        "images": [],
    }


# =============================================================================
# Mock Services
# =============================================================================
@pytest.fixture
def mock_verification_service():
    """인증 서비스 Mock"""
    from snu_toto.app.auth.services import VerificationService
    mock = AsyncMock(spec=VerificationService)
    # Default behaviors
    mock.check_rate_limit.return_value = True
    mock.create_verification_code.return_value = "123456"
    mock.verify_code.return_value = True
    return mock


# =============================================================================
# 헬퍼 함수
# =============================================================================
def auth_header(token: str) -> dict:
    """Authorization 헤더 생성"""
    return {"Authorization": f"Bearer {token}"}


def malformed_auth_header() -> dict:
    """잘못된 형식의 Authorization 헤더"""
    return {"Authorization": "InvalidFormat token123"}


def expired_token_header() -> dict:
    """만료된 토큰 헤더 (테스트용 더미)"""
    return {"Authorization": "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwiZXhwIjoxfQ.invalid"}


def assert_error_response(response, status_code: int, error_code: str):
    """에러 응답 검증 헬퍼"""
    assert response.status_code == status_code
    data = response.json()
    assert data.get("error_code") == error_code, f"Expected {error_code}, got {data}"


# =============================================================================
# 공통 헬퍼 (Multipart 등)
# =============================================================================
def multipart_headers(token: str):
    # httpx handles boundary when files is passed, but we also need Auth
    return {"Authorization": f"Bearer {token}"}

# We need to pass 'files' to httpx to trigger multipart/form-data.
# Passing an empty dict might not trigger it if data is present.
# We pass a dummy file field that won't be used by the backend logic 
# (since image_files matches by name 'image_files' and this is 'ignore').
EMPTY_FILES = {"ignore_me": ("ignore.txt", b"", "text/plain")} 


import json
import uuid
from snu_toto.app.core.date_utils import get_kst_now
from datetime import timedelta

@pytest_asyncio.fixture
async def open_event_with_bets(async_client: AsyncClient, admin_token: str, auth_token: str) -> str:
    """베팅이 있는 OPEN 상태 이벤트 생성 (공용 픽스처)"""
    start_at = (get_kst_now() + timedelta(days=2) + timedelta(hours=1)).isoformat()
    end_at = (get_kst_now() + timedelta(days=3) + timedelta(hours=2)).isoformat()
    
    event_data = {
        "title": f"공용 테스트 이벤트 {uuid.uuid4()}",
        "description": "테스트용",
        "start_at": start_at,
        "end_at": end_at,
        "options": [
            {"name": "옵션A", "option_image_index": -1},
            {"name": "옵션B", "option_image_index": -1},
        ],
        "images": [],
    }
    
    # 이벤트 생성
    create_response = await async_client.post(
        "/api/events",
        data={"data": json.dumps(event_data)},
        files=EMPTY_FILES,
        headers=multipart_headers(admin_token),
    )
    assert create_response.status_code == 201
    event_id = create_response.json()["event_id"]
    option_id = create_response.json()["options"][0]["option_id"]
    
    # OPEN 상태로 변경
    await async_client.patch(
        f"/api/events/{event_id}/status",
        json={"status": "OPEN"},
        headers=auth_header(admin_token),
    )
    
    # 베팅 추가
    bet_res = await async_client.post(
        f"/api/events/{event_id}/bets",
        json={"option_id": option_id, "bet_amount": 100},
        headers=auth_header(auth_token),
    )
    assert bet_res.status_code == 201
    
    return event_id
