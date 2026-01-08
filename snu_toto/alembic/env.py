import asyncio
import sys
import os

from logging.config import fileConfig

from sqlalchemy.ext.asyncio import async_engine_from_config
from sqlalchemy import pool

from alembic import context

sys.path.append(os.path.join(os.getcwd(), "snu_toto"))


# Alembic을 통해 인식돼야 하는 모델
from app.core.database import Base
from app.core.config import DB_SETTINGS
from app.users.models import User, PointHistory
from app.events.models import Event, EventOption, EventImage
from app.bets.models import Bet

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

config.set_main_option("sqlalchemy.url", DB_SETTINGS.url)

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# add your model's MetaData object here
# for 'autogenerate' support
# from myapp import mymodel
# target_metadata = mymodel.Base.metadata
target_metadata = Base.metadata

# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.


def do_run_migrations(connection):
    # 내가 현재 연결한 DB 이름 (예: 'snutoto')만 감시하도록 필터 추가
    def include_object(object, name, type_, reflected, compare_to):
        if type_ == "table" and object.schema is not None:
            return False  # 다른 스키마(DB)의 테이블은 무시
        return True
    
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,              # 컬럼 타입 변경 감지
        include_object=include_object
    )
    with context.begin_transaction():
        context.run_migrations()

async def run_migrations_online():
    """비동기 방식으로 마이그레이션 실행"""
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()

if context.is_offline_mode():
    # 오프라인 모드 설정 (필요 시)
    context.configure(
        url=DB_SETTINGS.url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()
else:
    # 온라인 모드 실행
    asyncio.run(run_migrations_online())