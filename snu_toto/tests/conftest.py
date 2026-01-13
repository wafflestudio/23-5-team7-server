"""
SNU Toto 테스트 공통 픽스처 및 헬퍼 함수
기존 브랜치 코드와 호환되도록 작성
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

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    try:
        yield engine
    finally:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
        await engine.dispose()


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
@pytest_asyncio.fixture
async def async_client(db_session) -> AsyncGenerator[AsyncClient, None]:
    """비동기 HTTP 클라이언트 (의존성 오버라이드 포함)"""
    async def override_get_db_session():
        yield db_session

    app.dependency_overrides[get_db_session] = override_get_db_session

    transport = ASGITransport(app=app)
    async with AsyncClient(
        transport=transport, 
        base_url="http://test",
        follow_redirects=True
    ) as ac:
        yield ac
    
    app.dependency_overrides.clear()


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
async def auth_token(async_client: AsyncClient, user_signup_data: dict) -> str:
    """로그인 후 access_token 반환 (인증 완료된 유저 가정)"""
    # 가입
    await async_client.post("/api/users", json=user_signup_data)
    
    # 로그인 (이메일 인증 없이 테스트용)
    login_data = {
        "email": user_signup_data["email"],
        "password": user_signup_data["password"],
    }
    res = await async_client.post("/api/auth/login", json=login_data)
    data = res.json()
    return data.get("access_token", "")


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
