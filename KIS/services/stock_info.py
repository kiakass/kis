# 5. services/stock_info.py
# python

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