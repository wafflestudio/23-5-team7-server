from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from snu_toto.app.users.models import User
from snu_toto.app.users.schemas import SocialType, UserSignupRequest
from snu_toto.app.core.security import get_password_hash
from snu_toto.app.users.repositories import UserRepository
from snu_toto.app.users.exceptions import (
    EmailAlreadyExistsException, 
    NicknameAlreadyExistsException, 
    SocialIdAlreadyExistsException
)

class UserService:
    def __init__(self, db: AsyncSession):
        self.user_repo = UserRepository(db)
        self.db = db

    async def signup(self, user_in: UserSignupRequest) -> User:
        # 중복 검증 (Repository 이용)
        if await self.user_repo.get_by_email(user_in.email):
            raise EmailAlreadyExistsException()

        if await self.user_repo.get_by_nickname(user_in.nickname):
            raise NicknameAlreadyExistsException()

        # 가입 유형에 따라, LOCAL이면 social_id를 비우고, 소셜이면 password를 비우기
        hashed_password = None
        social_id = None

        if user_in.social_type == SocialType.LOCAL:
            # 로컬 가입: 비밀번호 해싱 필수, 소셜 ID는 무시
            hashed_password = get_password_hash(user_in.password)
        else:
            # 소셜 가입: 소셜 ID 저장, 비밀번호는 무시
            if await self.user_repo.get_by_social_id(user_in.social_type.value, user_in.social_id):
                raise SocialIdAlreadyExistsException()
            social_id = user_in.social_id

        # 객체 생성 및 저장
        new_user = User(
            email=user_in.email,
            hashed_password=hashed_password,
            nickname=user_in.nickname,
            points=10000,
            role="USER",
            is_verified=False,
            is_snu_verified=False,
            social_type=user_in.social_type.value,
            social_id=social_id
        )

        await self.user_repo.create(new_user)
        
        # 트랜잭션 확정
        try:
            await self.db.commit()
            await self.db.refresh(new_user)
        except Exception as e:
            await self.db.rollback()
            raise e
            
        return new_user

    async def get_top_users_with_total(self, limit: int):
        # 전체 유저 수 조회 (순위에 포함될 대상)
        total_query = select(func.count(User.user_id))
        total_res = await self.db.execute(total_query)
        total_count = total_res.scalar()

        # 랭킹 데이터 조회 (포인트 내림차순, 동점 시 ID 오름차순으로 고정)
        ranking_query = (
            select(User)
            .order_by(User.points.desc(), User.user_id.asc())
            .limit(limit)
        )
        ranking_res = await self.db.execute(ranking_query)
        users = ranking_res.scalars().all()

        # 순위 부여
        rankings = [
            {"rank": i + 1, "nickname": u.nickname, "points": u.points}
            for i, u in enumerate(users)
        ]

        return {"total_count": total_count, "rankings": rankings}