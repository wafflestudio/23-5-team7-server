import math
from typing import List
from sqlalchemy import false
from sqlalchemy.ext.asyncio import AsyncSession
from snu_toto.app.events.models import Event, EventStatus
from snu_toto.app.bets.models import Bet, BetStatus
from snu_toto.app.users.models import User, PointHistory, PointReason
from .calculator import SettlementCalculator

class SettlementEngine:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def run_settle(self, event: Event, winner_option_ids: List[str]):
        """전체 정산 프로세스 실행"""
        
        # 배당률 계산
        ratio = SettlementCalculator.calculate_dividend_ratio(event.options, winner_option_ids)
        
        if ratio == 0:
            # 적중자가 없는 경우 -> 전액 환불
            await self._process_refund(event.bets)
        else:
            # 정상 배당금 지급
            await self._process_payout(event.bets, winner_option_ids, ratio)

        # 옵션 상태 업데이트 (WIN/LOSE)
        for opt in event.options:
            opt.is_winner = (opt.option_id in winner_option_ids)

        # 이벤트 상태 변경
        event.status = EventStatus.SETTLED
    
    async def run_cancel(self, event: Event):
        """이벤트 취소 프로세스 실행"""
        # 전액 환불
        print("sdafsfafs")
        await self._process_refund(event.bets)

    async def _process_payout(self, bets: List[Bet], winner_option_ids: List[str], ratio: float):
        """적중자에게 포인트 지급 및 낙첨 처리"""
        for bet in bets:
            user = bet.user
            if bet.option_id in winner_option_ids:
                # 적중
                payout_amount = SettlementCalculator.calculate_payout(bet.amount, ratio)
                user.points += payout_amount
                bet.status = BetStatus.WIN
                
                # 포인트 히스토리 생성
                self.session.add(PointHistory(
                    user_id=user.user_id,
                    bet_id=bet.bet_id,
                    change_amount=payout_amount,
                    reason=PointReason.WIN,
                    points_after=user.points
                ))
            else:
                # 낙첨
                bet.status = BetStatus.LOSE

    async def _process_refund(self, bets: List[Bet]):
        """전액 환불 처리 (적중자 0명/이벤트 취소일 때)"""
        for bet in bets:
            user = bet.user
            user.points += bet.amount
            bet.status = BetStatus.REFUNDED
            
            self.session.add(PointHistory(
                user_id=user.user_id,
                bet_id=bet.bet_id,
                change_amount=bet.amount,
                reason=PointReason.REFUND,
                points_after=user.points
            ))