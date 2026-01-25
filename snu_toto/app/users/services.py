from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
from snu_toto.app.users.models import User
from snu_toto.app.users.schemas import SocialType, UserSignupRequest, UserBetsResponse, UserBetItem
from snu_toto.app.core.security import get_password_hash
from snu_toto.app.users.repositories import UserRepository
from snu_toto.app.users.exceptions import (
    EmailAlreadyExistsException, 
    NicknameAlreadyExistsException, 
    SocialIdAlreadyExistsException
)
from snu_toto.app.bets.models import BetStatus

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

    async def get_my_bets(
        self,
        user_id: str,
        status: Optional[BetStatus] = None,
        limit: int = 20,
        offset: int = 0
    ) -> UserBetsResponse:
        """
        사용자의 베팅 내역 조회
        """
        bets_data, total_count = await self.user_repo.get_user_bets(
            user_id=user_id,
            status=status,
            limit=limit,
            offset=offset
        )
        
        # 딕셔너리를 Pydantic 모델로 변환
        bet_items = [UserBetItem(**bet) for bet in bets_data]
        
        return UserBetsResponse(
            total_count=total_count,
            bets=bet_items
        )