from typing import List
from snu_toto.app.events.models import EventOption

class SettlementCalculator:
    @staticmethod
    def calculate_dividend_ratio(all_options: List[EventOption], winner_option_ids: List[str]) -> float:
        """
        배당률 계산
        - Total Pool: 모든 옵션의 베팅 총액 합산
        - Winning Pool: 승리한 옵션들의 베팅 총액 합산
        """
        total_pool = sum(opt.option_total_amount for opt in all_options)
        winning_pool = sum(opt.option_total_amount for opt in all_options if opt.option_id in winner_option_ids)

        # 적중자가 아무도 없는 경우 배당률은 0 (이후 환불 처리를 위해 사용 가능)
        if winning_pool == 0:
            return 0.0
        
        return total_pool / winning_pool

    @staticmethod
    def calculate_payout(bet_amount: int, ratio: float) -> int:
        """포인트 지급액 계산 (소수점 버림 처리)"""
        return int(bet_amount * ratio)