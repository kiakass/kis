# 7. main.py
#python
import time
import datetime
from models.stock_config import StockConfig
from services.notification import NotificationService
from services.authentication import AuthenticationService
from services.stock_info import StockInfoService
from services.account import AccountService
from services.trading import TradingService

class AutoTradeBot:
    def __init__(self, config_path='config/config.yaml'):
        # 컴포넌트 초기화
        self.config = StockConfig(config_path)
        self.notification = NotificationService(self.config.DISCORD_WEBHOOK_URL)
        self.auth_service = AuthenticationService(self.config)
        self.stock_info = StockInfoService(self.config, self.auth_service)
        self.account_service = AccountService(self.config, self.auth_service, self.notification)
        self.trading_service = TradingService(self.config, self.auth_service, self.notification)

    def run(self):
        try:
            # 액세스 토큰 획득
            self.auth_service.get_access_token()

            # 트레이딩 파라미터
            symbol_list = ["005930", "035720", "000660", "069500"]
            bought_list = []
            total_cash = self.account_service.get_balance()
            stock_dict = self.account_service.get_stock_balance()
            
            for sym in stock_dict.keys():
                bought_list.append(sym)

            target_buy_count = 3
            buy_percent = 0.33
            buy_amount = total_cash * buy_percent
            soldout = False

            self.notification.send_message("===국내 주식 자동매매 프로그램을 시작합니다===")

            while True:
                # 기존 트레이딩 로직 (생략)
                # 시간대별 매수/매도 로직 유지

                time.sleep(1)  # CPU 사용률 제어

        except Exception as e:
            self.notification.send_message(f"[오류 발생] {e}")
            time.sleep(1)

if __name__ == "__main__":
    bot = AutoTradeBot()
    bot.run()
#