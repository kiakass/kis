# 프로젝트 구조 생성을 위한 디렉토리 및 파일 내용

# 1. config/config.yaml
#yaml
# 기존 config 파일과 동일
APP_KEY: your_app_key
APP_SECRET: your_app_secret
CANO: your_account_number
ACNT_PRDT_CD: your_product_code
DISCORD_WEBHOOK_URL: your_discord_webhook_url
URL_BASE: https://openapi.xyz.com
'''#'''

# 2. models/stock_config.py
# python
import yaml

class StockConfig:
    def __init__(self, config_path='config/config.yaml'):
        try:
            with open(config_path, encoding='UTF-8') as f:
                self._cfg = yaml.load(f, Loader=yaml.FullLoader)
            
            self.APP_KEY = self._cfg['APP_KEY']
            self.APP_SECRET = self._cfg['APP_SECRET']
            self.CANO = self._cfg['CANO']
            self.ACNT_PRDT_CD = self._cfg['ACNT_PRDT_CD']
            self.DISCORD_WEBHOOK_URL = self._cfg['DISCORD_WEBHOOK_URL']
            self.URL_BASE = self._cfg['URL_BASE']
            self.ACCESS_TOKEN = ""
        except FileNotFoundError:
            raise FileNotFoundError(f"Configuration file not found: {config_path}")
        except KeyError as e:
            raise KeyError(f"Missing configuration key: {e}")
#

# 3. services/notification.py
#python
import requests
import datetime

class NotificationService:
    def __init__(self, webhook_url):
        self.webhook_url = webhook_url
    
    def send_message(self, msg):
        """Discord 메시지 전송"""
        now = datetime.datetime.now()
        message = {"content": f"[{now.strftime('%Y-%m-%d %H:%M:%S')}] {str(msg)}"}
        try:
            response = requests.post(self.webhook_url, data=message)
            response.raise_for_status()
            print(message)
        except requests.exceptions.RequestException as e:
            print(f"Notification failed: {e}")
#

# 4. services/authentication.py
#python
import requests
import json

class AuthenticationService:
    def __init__(self, config):
        self.config = config
    
    def get_access_token(self):
        """토큰 발급"""
        headers = {"content-type": "application/json"}
        body = {
            "grant_type": "client_credentials",
            "appkey": self.config.APP_KEY, 
            "appsecret": self.config.APP_SECRET
        }
        PATH = "oauth2/tokenP"
        URL = f"{self.config.URL_BASE}/{PATH}"
        
        try:
            res = requests.post(URL, headers=headers, data=json.dumps(body))
            res.raise_for_status()
            self.config.ACCESS_TOKEN = res.json()["access_token"]
            return self.config.ACCESS_TOKEN
        except requests.exceptions.RequestException as e:
            raise RuntimeError(f"Token acquisition failed: {e}")
    
    def hashkey(self, datas):
        """API 요청 암호화"""
        PATH = "uapi/hashkey"
        URL = f"{self.config.URL_BASE}/{PATH}"
        headers = {
            'content-Type': 'application/json',
            'appKey': self.config.APP_KEY,
            'appSecret': self.config.APP_SECRET,
        }
        
        try:
            res = requests.post(URL, headers=headers, data=json.dumps(datas))
            res.raise_for_status()
            return res.json()["HASH"]
        except requests.exceptions.RequestException as e:
            raise RuntimeError(f"Hashkey generation failed: {e}")
#

# 5. services/stock_info.py
#python
import requests
from strategies.volatility_breakout import VolatilityBreakoutStrategy

class StockInfoService:
    def __init__(self, config, auth_service):
        self.config = config
        self.auth_service = auth_service
        self.strategy = VolatilityBreakoutStrategy()
    
    def get_current_price(self, code="005930"):
        """현재가 조회"""
        PATH = "uapi/domestic-stock/v1/quotations/inquire-price"
        URL = f"{self.config.URL_BASE}/{PATH}"
        headers = {
            "Content-Type": "application/json", 
            "authorization": f"Bearer {self.config.ACCESS_TOKEN}",
            "appKey": self.config.APP_KEY,
            "appSecret": self.config.APP_SECRET,
            "tr_id": "FHKST01010100"
        }
        params = {
            "fid_cond_mrkt_div_code": "J",
            "fid_input_iscd": code,
        }
        
        try:
            res = requests.get(URL, headers=headers, params=params)
            res.raise_for_status()
            return int(res.json()['output']['stck_prpr'])
        except requests.exceptions.RequestException as e:
            raise RuntimeError(f"Current price retrieval failed: {e}")

    def get_target_price(self, code="005930"):
        """변동성 돌파 전략 목표가 계산"""
        PATH = "uapi/domestic-stock/v1/quotations/inquire-daily-price"
        URL = f"{self.config.URL_BASE}/{PATH}"
        headers = {
            "Content-Type": "application/json", 
            "authorization": f"Bearer {self.config.ACCESS_TOKEN}",
            "appKey": self.config.APP_KEY,
            "appSecret": self.config.APP_SECRET,
            "tr_id": "FHKST01010400"
        }
        params = {
            "fid_cond_mrkt_div_code": "J",
            "fid_input_iscd": code,
            "fid_org_adj_prc": "1",
            "fid_period_div_code": "D"
        }
        
        try:
            res = requests.get(URL, headers=headers, params=params)
            res.raise_for_status()
            data = res.json()['output']
            
            stck_oprc = int(data[0]['stck_oprc'])  # 오늘 시가
            stck_hgpr = int(data[1]['stck_hgpr'])  # 전일 고가
            stck_lwpr = int(data[1]['stck_lwpr'])  # 전일 저가
            
            return self.strategy.calculate_target_price(stck_oprc, stck_hgpr, stck_lwpr)
        except requests.exceptions.RequestException as e:
            raise RuntimeError(f"Target price calculation failed: {e}")
#

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

# 8. requirements.txt
#
requests==2.26.0
pyyaml==6.0
#
'''
추가로 필요한 파일들:
- `services/account.py`
- `services/trading.py`
- `utils/error_handler.py`

프로젝트 구조의 주요 개선사항:
1. 각 클래스의 책임 명확화
2. 에러 핸들링 강화
3. 전략 로직 분리
4. 모듈성 및 확장성 증대

실행 방법:
#bash
# 가상환경 생성 및 활성화
python -m venv venv
source venv/bin/activate  # 리눅스/맥
# or
venv\Scripts\activate  # 윈도우

# 의존성 설치
pip install -r requirements.txt

# 실행
python main.py
#

이 구조는 기존 단일 파일 대비 훨씬 더 유연하고 확장 가능한 아키텍처를 제공합니다.

korea_stock_auto_trade/
│
├── config/
│   └── config.yaml          # 설정 파일
│
├── services/
│   ├── __init__.py
│   ├── authentication.py     # AuthenticationService
│   ├── notification.py       # NotificationService
│   ├── stock_info.py         # StockInfoService
│   ├── account.py            # AccountService
│   └── trading.py            # TradingService
│
├── models/
│   ├── __init__.py
│   └── stock_config.py       # StockConfig 클래스
│
├── strategies/
│   ├── __init__.py
│   └── volatility_breakout.py  # 변동성 돌파 전략 관련 로직
│
├── utils/
│   ├── __init__.py
│   └── error_handler.py      # 공통 예외 처리 유틸리티
│
├── main.py                   # AutoTradeBot 메인 실행 스크립트
└── requirements.txt          # 의존성 관리
'''