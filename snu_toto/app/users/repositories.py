from typing import Annotated, Optional, List
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import and_, delete, desc, func, or_, update
from snu_toto.app.core.config import AUTH_SETTINGS
from snu_toto.app.core.date_utils import get_kst_now
from snu_toto.app.users.models import User, PointHistory, PointReason, UserWithdrawal
from snu_toto.app.bets.models import Bet, BetStatus
from snu_toto.app.events.models import Event, EventOption
from snu_toto.app.core.database import get_db_session
from datetime import datetime, timedelta


class UserRepository:
    def __init__(self, db: Annotated[AsyncSession, Depends(get_db_session)]):
        self.db = db

    async def get_by_id(self, user_id: str) -> Optional[User]:
        """ID로 사용자 조회"""
        result = await self.db.execute(select(User).filter(User.user_id == user_id))
        return result.scalar_one_or_none()

    async def get_by_email(self, email: str) -> Optional[User]:
        """이메일로 사용자 조회"""
        result = await self.db.execute(select(User).filter(User.email == email))
        return result.scalar_one_or_none()

    async def get_by_nickname(self, nickname: str) -> Optional[User]:
        """닉네임으로 사용자 조회"""
        result = await self.db.execute(select(User).filter(User.nickname == nickname))
        return result.scalar_one_or_none()

    async def get_by_social_id(self, social_type: str, social_id: str) -> Optional[User]:
        """소셜 타입과 ID로 사용자 조회"""
        result = await self.db.execute(
            select(User).filter(
                User.social_type == social_type,
                User.social_id == social_id
            )
        )
        return result.scalar_one_or_none()

    async def create(self, user: User) -> User:
        """사용자 객체를 DB에 저장"""
        self.db.add(user)
        await self.db.flush()
        
        # 신규 가입 포인트 기록 저장
        self.db.add(PointHistory(
                    user_id=user.user_id,
                    change_amount=user.points,
                    reason=PointReason.SIGNUP,
                    points_after=user.points
                ))
        return user

    async def get_user_bets(
        self,
        user_id: str,
        status: Optional[BetStatus] = None,
        limit: int = 20,
        offset: int = 0
    ) -> tuple[List[dict], int]:
        """
        사용자의 베팅 내역 조회 (참여 중인 베팅 확인)
        """
        # 베팅 내역 조회 쿼리 (Event, EventOption 조인)
        query = (
            select(
                Bet.bet_id,
                Bet.event_id,
                Event.title.label("event_title"),
                Bet.option_id,
                EventOption.name.label("option_name"),
                Bet.amount,
                Bet.status,
                Bet.created_at
            )
            .join(Event, Bet.event_id == Event.event_id)
            .join(EventOption, Bet.option_id == EventOption.option_id)
            .where(Bet.user_id == user_id)
        )
        
        # 상태 필터링
        if status:
            query = query.where(Bet.status == status)
        
        # 최신 순으로 정렬
        query = query.order_by(Bet.created_at.desc())
        
        # 전체 개수 조회
        count_query = select(func.count()).select_from(Bet).where(Bet.user_id == user_id)
        if status:
            count_query = count_query.where(Bet.status == status)
        
        total_result = await self.db.execute(count_query)
        total_count = total_result.scalar()
        
        # 페이지네이션 적용
        query = query.limit(limit).offset(offset)
        
        # 실행
        result = await self.db.execute(query)
        bets = result.mappings().all()
        
        return [dict(bet) for bet in bets], total_count

    async def get_user_point_history(
        self,
        user_id: str,
        reason: Optional[PointReason] = None,
        limit: int = 20,
        offset: int = 0
    ) -> tuple[List[dict], int]:
        """
        사용자의 포인트 내역 조회 (베팅 세부 정보 포함)
        """
        # 포인트 내역 조회 쿼리 (Bet, Event, EventOption 조인하여 베팅 세부 정보 포함)
        query = (
            select(
                PointHistory.history_id,
                PointHistory.reason,
                PointHistory.change_amount,
                PointHistory.points_after,
                PointHistory.bet_id,
                Bet.event_id.label("event_id"),
                Event.title.label("event_title"),
                Bet.option_id.label("option_id"),
                EventOption.name.label("option_name"),
                PointHistory.created_at
            )
            .outerjoin(Bet, PointHistory.bet_id == Bet.bet_id)
            .outerjoin(Event, Bet.event_id == Event.event_id)
            .outerjoin(EventOption, Bet.option_id == EventOption.option_id)
            .where(PointHistory.user_id == user_id)
        )
        
        # reason 필터링
        if reason:
            query = query.where(PointHistory.reason == reason)
        
        # 최신 순으로 정렬
        query = query.order_by(PointHistory.created_at.desc())
        
        # 전체 개수 조회
        count_query = select(func.count()).select_from(PointHistory).where(PointHistory.user_id == user_id)
        if reason:
            count_query = count_query.where(PointHistory.reason == reason)
        
        total_result = await self.db.execute(count_query)
        total_count = total_result.scalar()
        
        # 페이지네이션 적용
        query = query.limit(limit).offset(offset)
        
        # 실행
        result = await self.db.execute(query)
        histories = result.mappings().all()
        
        return [dict(history) for history in histories], total_count

    async def get_user_stats(self, user_id: str) -> dict:
        """
        사용자의 통계 데이터 조회
        """
        # 현재 포인트
        user = await self.get_by_id(user_id)
        current_balance = user.points if user else 0
        
        # 포인트 통계 (total_earned, total_spent)
        earned_query = select(func.sum(PointHistory.change_amount)).where(
            PointHistory.user_id == user_id,
            PointHistory.change_amount > 0
        )
        spent_query = select(func.sum(PointHistory.change_amount)).where(
            PointHistory.user_id == user_id,
            PointHistory.change_amount < 0
        )
        
        earned_result = await self.db.execute(earned_query)
        spent_result = await self.db.execute(spent_query)
        
        total_earned = earned_result.scalar() or 0
        total_spent = abs(spent_result.scalar() or 0)
        
        # 베팅 통계
        total_bets_query = select(func.count()).select_from(Bet).where(Bet.user_id == user_id)
        pending_query = select(func.count()).select_from(Bet).where(
            Bet.user_id == user_id,
            Bet.status == BetStatus.PENDING
        )
        win_query = select(func.count()).select_from(Bet).where(
            Bet.user_id == user_id,
            Bet.status == BetStatus.WIN
        )
        lose_query = select(func.count()).select_from(Bet).where(
            Bet.user_id == user_id,
            Bet.status == BetStatus.LOSE
        )
        refunded_query = select(func.count()).select_from(Bet).where(
            Bet.user_id == user_id,
            Bet.status == BetStatus.REFUNDED
        )
        
        total_bets = (await self.db.execute(total_bets_query)).scalar() or 0
        pending_count = (await self.db.execute(pending_query)).scalar() or 0
        win_count = (await self.db.execute(win_query)).scalar() or 0
        lose_count = (await self.db.execute(lose_query)).scalar() or 0
        refunded_count = (await self.db.execute(refunded_query)).scalar() or 0
        
        # 승률 계산
        settled_bets = win_count + lose_count
        win_rate = round(win_count / settled_bets * 100, 1) if settled_bets > 0 else 0.0
        
        return {
            "points": {
                "current_balance": current_balance,
                "total_earned": total_earned,
                "total_spent": total_spent
            },
            "bets": {
                "total_bets_count": total_bets,
                "pending_count": pending_count,
                "win_count": win_count,
                "lose_count": lose_count,
                "refunded_count": refunded_count,
                "win_rate": win_rate
            }
        }

    async def get_user_ranking(self, user_id: str) -> dict:
        """
        사용자의 랭킹 정보 조회 (Redis에서 읽기만)
        실제 계산은 매시 정각 배치 작업에서 수행됨
        
        Returns:
            dict: 랭킹 정보 (Redis에서 조회)
        """
        from redis.asyncio import from_url
        from snu_toto.app.core.config import REDIS_SETTINGS
        import json
        
        redis = await from_url(REDIS_SETTINGS.URL, decode_responses=True)
        
        try:
            cache_key = f"user_ranking:{user_id}"
            cached = await redis.get(cache_key)
            
            if cached:
                return json.loads(cached)
            
            # 캐시 없으면 기본값 반환 (배치 작업 대기 중)
            user = await self.get_by_id(user_id)
            return {
                "rank": 0,
                "total_users": 0,
                "percentile": 0.0,
                "my_points": user.points if user else 0
            }
        finally:
            await redis.close()
    
    async def get_global_ranking_data(self) -> dict:
        """Redis에서 전체 유저 수와 상위 랭킹 리스트를 가져옴"""
        from redis.asyncio import from_url
        from snu_toto.app.core.config import REDIS_SETTINGS
        import json

        redis = await from_url(REDIS_SETTINGS.URL, decode_responses=True)
        try:
            keys = ["ranking:total_count", "ranking:top_list", "ranking:updated_at"]
            values = await redis.mget(keys)
            
            return {
                "total_count": int(values[0]) if values[0] else 0,
                "top_list": json.loads(values[1]) if values[1] else [],
                "updated_at": values[2] if values[2] else get_kst_now().isoformat()
            }
        finally:
            await redis.close()

    async def update_user(self, user: User) -> User:
        """사용자 정보 업데이트"""
        await self.db.flush()
        return user
    
    async def update_user_role(self, user_id: str, new_role: str) -> None:
        """유저의 역할을 업데이트"""
        await self.db.execute(
            update(User)
            .where(User.user_id == user_id)
            .values(role=new_role)
        )
    
    async def update_user_suspension(
        self, 
        user_id: str, 
        suspended_until: datetime, 
        reason: str
    ) -> None:
        """유저의 정지 정보를 업데이트"""
        await self.db.execute(
            update(User)
            .where(User.user_id == user_id)
            .values(
                suspended_until=suspended_until,
                suspension_reason=reason
            )
        )
    
    async def clear_suspension(self, user: User) -> None:
        """DB에서 정지 정보를 삭제하고 메모리 객체도 동기화"""
        user.suspended_until = None
        user.suspension_reason = None
        await self.db.flush()

    async def anonymize_and_withdraw(self, user: User, hashed_email: str):
        """유저 정보를 비식별화하고 탈퇴 이력을 한 트랜잭션으로 기록"""
        # 유저 정보 비식별화 (Unique 제약 충돌 방지를 위해 UUID 활용)
        unique_id = str(user.user_id)[:12]
        user.email = f"deleted_{unique_id}_{get_kst_now().timestamp()}@snu.ac.kr"
        user.nickname = f"탈퇴유저_{unique_id}"
        user.hashed_password = None
        user.social_id = None
        user.is_deleted = True
        user.points = 0

        # 탈퇴 이력 추가
        withdrawal = UserWithdrawal(
            user_id=user.user_id,
            hashed_email=hashed_email
        )
        self.db.add(withdrawal)
        
        await self.db.commit()
    
    async def get_latest_withdrawal_by_hash(self, hashed_email: str) -> UserWithdrawal | None:
        """이메일 해시로 가장 최근 탈퇴 이력 조회"""
        query = (
            select(UserWithdrawal)
            .where(UserWithdrawal.hashed_email == hashed_email)
            .order_by(desc(UserWithdrawal.deleted_at))
            .limit(1)
        )
        result = await self.db.execute(query)
        return result.scalar_one_or_none()
    
    async def get_admin_user_list(self, page: int, limit: int, search: Optional[str], status_filter: Optional[str]):
        query = select(User)

        # 상태 필터링
        now = datetime.now()
        if status_filter == "DELETED":
            query = query.where(User.is_deleted == True)
        elif status_filter == "SUSPENDED":
            query = query.where(and_(User.is_deleted == False, User.suspended_until > now))
        elif status_filter == "ACTIVE":
            query = query.where(and_(
                User.is_deleted == False,
                or_(User.suspended_until == None, User.suspended_until <= now)
            ))

        # 검색 필터링
        if search:
            query = query.where(or_(User.nickname.contains(search), User.email.contains(search)))

        # 전체 개수 조회 (페이지네이션용)
        count_query = select(func.count()).select_from(query.subquery())
        total_res = await self.db.execute(count_query)
        total_count = total_res.scalar() or 0

        # 데이터 조회 (최신순 정렬 및 페이징)
        query = query.order_by(User.created_at.desc()).offset((page - 1) * limit).limit(limit)
        result = await self.db.execute(query)
        users = result.scalars().all()

        return users, total_count
    
    async def delete_expired_unverified_users(
            self, 
            expiry_minutes: int = AUTH_SETTINGS.SHORT_SESSION_LIFESPAN + 1, 
            long_expiry_hours: int = 6
    ):
        """
        SNU 인증을 하지 않은 유저 삭제
        조건: (미인증) AND [ {(가입 > 16분) AND (마지막 활동 > 16분)} OR (가입 > 6시간) ]
        """
        now = get_kst_now()
        soft_limit = now - timedelta(minutes=expiry_minutes)
        hard_limit = now - timedelta(hours=long_expiry_hours)

        try:
            # 삭제 대상 ID 조회
            target_query = (
                select(User.user_id)
                .where(
                    and_(
                        User.is_snu_verified == False,
                        or_(
                            and_(
                                User.created_at < soft_limit,
                                User.last_login_at < soft_limit
                            ),
                            User.created_at < hard_limit
                        )
                    )
                )
            )
            
            result = await self.db.execute(target_query)
            target_user_ids = result.scalars().all() # ID 리스트 확보

            if not target_user_ids:
                return 0

            # PointHistory에서 해당 유저들의 기록 삭제
            await self.db.execute(
                delete(PointHistory)
                .where(PointHistory.user_id.in_(target_user_ids))
            )

            # User 테이블에서 해당 유저들을 최종 삭제
            delete_result = await self.db.execute(
                delete(User)
                .where(User.user_id.in_(target_user_ids))
            )
            
            deleted_count = delete_result.rowcount
            return deleted_count

        except Exception as e:
            print(f"[Cleanup Error] {e}")
            raise e
    
    async def update_last_login(self, user_id: str) -> None:
        """사용자의 last_login_at 시각을 현재시각으로 업데이트"""
        await self.db.execute(
            update(User)
            .where(User.user_id == user_id)
            .values(last_login_at=get_kst_now())
        )
        await self.db.commit()