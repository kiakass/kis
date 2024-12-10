# 6. strategies/volatility_breakout.py
#python
class VolatilityBreakoutStrategy:
    def calculate_target_price(self, today_open, yesterday_high, yesterday_low, k=0.5):
        """
        변동성 돌파 전략에 따른 목표가 계산
        
        :param today_open: 오늘의 시가
        :param yesterday_high: 전일 고가
        :param yesterday_low: 전일 저가
        :param k: 변동성 배수 (기본값 0.5)
        :return: 목표 매수 가격
        """
        volatility = yesterday_high - yesterday_low
        target_price = today_open + (volatility * k)
        return target_price
#