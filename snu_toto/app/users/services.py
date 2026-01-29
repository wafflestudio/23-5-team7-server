from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
from snu_toto.app.users.models import User, PointReason
from snu_toto.app.users.schemas import (
    SocialType, 
    UserSignupRequest,
    UserBetsResponse,
    UserBetItem,
    UserPointHistoryResponse,
    UserPointHistoryItem,
    UserProfileResponse,
    UserStatsResponse,
    UserPointsStats,
    UserBetsStats,
    UserRankingResponse
)
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
            social_id=social_id,
            suspended_until=None,
            suspension_reason=None
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
        사용자의 베팅 내역 조회 (참여 중인 베팅 확인)
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

    async def get_my_point_history(
        self,
        user_id: str,
        reason: Optional[PointReason] = None,
        limit: int = 20,
        offset: int = 0
    ) -> UserPointHistoryResponse:
        """
        사용자의 포인트 내역 조회
        """
        # 현재 잔액 조회
        user = await self.user_repo.get_by_id(user_id)
        current_balance = user.points
        
        # 포인트 내역 조회
        histories_data, total_count = await self.user_repo.get_user_point_history(
            user_id=user_id,
            reason=reason,
            limit=limit,
            offset=offset
        )
        
        # 딕셔너리를 Pydantic 모델로 변환
        history_items = [UserPointHistoryItem(**history) for history in histories_data]
        
        return UserPointHistoryResponse(
            current_balance=current_balance,
            total_count=total_count,
            history=history_items
        )

    async def get_my_profile(self, user_id: str) -> UserProfileResponse:
        """
        사용자의 프로필 정보 조회
        """
        user = await self.user_repo.get_by_id(user_id)
        return UserProfileResponse.model_validate(user)

    async def get_my_stats(self, user_id: str) -> UserStatsResponse:
        """
        사용자의 통계 정보 조회
        """
        stats_data = await self.user_repo.get_user_stats(user_id)
        
        return UserStatsResponse(
            points=UserPointsStats(**stats_data["points"]),
            bets=UserBetsStats(**stats_data["bets"])
        )

    async def get_my_ranking(self, user_id: str) -> UserRankingResponse:
        """
        사용자의 랜킹 정보 조회
        """
        ranking_data = await self.user_repo.get_user_ranking(user_id)
        return UserRankingResponse(**ranking_data)

    async def update_nickname(self, user_id: str, request) -> dict:
        """
        사용자 닉네임 변경
        """
        from snu_toto.app.users.exceptions import NicknameAlreadyExistsException
        
        # 닉네임 중복 체크 (자기 자신 제외)
        existing_user = await self.user_repo.get_by_nickname(request.nickname)
        if existing_user and existing_user.user_id != user_id:
            raise NicknameAlreadyExistsException()
        
        # 사용자 조회 및 닉네임 업데이트
        user = await self.user_repo.get_by_id(user_id)
        user.nickname = request.nickname
        await self.user_repo.update_user(user)
        
        return {
            "message": "닉네임이 성공적으로 변경되었습니다.",
            "nickname": request.nickname
        }
      
    async def get_top_users_with_total(self, limit: int) -> UserRankingResponse:
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

        return UserRankingResponse(total_count=total_count, rankings=rankings)
