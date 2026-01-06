FROM python:3.12-slim
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

# 의존성 파일 복사
COPY pyproject.toml uv.lock ./

# 가상환경 생성 및 패키지 설치
RUN uv venv
RUN uv sync --frozen --no-cache

# 전체 소스 코드 복사
COPY . .

EXPOSE 8080

CMD ["uv", "run", "uvicorn", "snu_toto.main:app", "--host", "0.0.0.0", "--port", "8080"]