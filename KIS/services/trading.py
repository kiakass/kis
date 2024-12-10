import requests
import json

class TradingService:
    def __init__(self, config, auth_service, notification_service):
        self.config = config
        self.auth_service = auth_service
        self.notification = notification_service
    
    def buy_stock(self, symbol, quantity, price):
        """
        주식 매수 함수
        :param symbol: 종목 코드
        :param quantity: 매수 수량
        :param price: 매수 가격
        """
        PATH = "uapi/domestic-stock/v1/trading/order-cash"
        URL = f"{self.config.URL_BASE}/{PATH}"
        headers = {
            "Content-Type": "application/json", 
            "authorization": f"Bearer {self.config.ACCESS_TOKEN}",
            "appKey": self.config.APP_KEY,
            "appSecret": self.config.APP_SECRET,
            "tr_id": "TTTC0802U",
            "custtype": "P"
        }
        body = {
            "CANO": self.config.CANO,
            "ACNT_PRDT_CD": self.config.ACNT_PRDT_CD,
            "PDNO": symbol,
            "ORD_DVSN": "01",  # 시장가
            "ORD_QTY": str(quantity),
            "ORD_UNPR": str(price)
        }
        
        try:
            res = requests.post(URL, headers=headers, data=json.dumps(body))
            res.raise_for_status()
            self.notification.send_message(f"[매수] {symbol}: {quantity}주, {price}원")
        except requests.exceptions.RequestException as e:
            self.notification.send_message(f"매수 주문 실패: {e}")
    
    def sell_stock(self, symbol, quantity):
        """
        주식 매도 함수
        :param symbol: 종목 코드
        :param quantity: 매도 수량
        """
        PATH = "uapi/domestic-stock/v1/trading/order-cash"
        URL = f"{self.config.URL_BASE}/{PATH}"
        headers = {
            "Content-Type": "application/json", 
            "authorization": f"Bearer {self.config.ACCESS_TOKEN}",
            "appKey": self.config.APP_KEY,
            "appSecret": self.config.APP_SECRET,
            "tr_id": "TTTC0801U",
            "custtype": "P"
        }
        body = {
            "CANO": self.config.CANO,
            "ACNT_PRDT_CD": self.config.ACNT_PRDT_CD,
            "PDNO": symbol,
            "ORD_DVSN": "01",  # 시장가
            "ORD_QTY": str(quantity)
        }
        
        try:
            res = requests.post(URL, headers=headers, data=json.dumps(body))
            res.raise_for_status()
            self.notification.send_message(f"[매도] {symbol}: {quantity}주")
        except requests.exceptions.RequestException as e:
            self.notification.send_message(f"매도 주문 실패: {e}")