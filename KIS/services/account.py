import requests
import json

class AccountService:
    def __init__(self, config, auth_service, notification_service):
        self.config = config
        self.auth_service = auth_service
        self.notification = notification_service
    
    def get_balance(self):
        """
        계좌 잔고 조회
        :return: 총 현금 잔고
        """
        PATH = "uapi/domestic-stock/v1/trading/inquire-balance"
        URL = f"{self.config.URL_BASE}/{PATH}"
        headers = {
            "Content-Type": "application/json", 
            "authorization": f"Bearer {self.config.ACCESS_TOKEN}",
            "appKey": self.config.APP_KEY,
            "appSecret": self.config.APP_SECRET,
            "tr_id": "TTTC8434R"
        }
        params = {
            "CANO": self.config.CANO,
            "ACNT_PRDT_CD": self.config.ACNT_PRDT_CD,
            "AFHR_FLPR_YN": "N",
            "OFL_YN": "",
            "INQR_DVSN": "02",
            "UNPR_DVSN": "01",
            "FUND_STTL_DVSN_CD": "40",
            "FNCG_AMT_AUTO_RDPT_YN": "N"
        }
        
        try:
            res = requests.get(URL, headers=headers, params=params)
            res.raise_for_status()
            output = res.json()['output1']
            total_cash = int(output[0]['dnca_tot_amt'])
            self.notification.send_message(f"현재 계좌 잔고: {total_cash}원")
            return total_cash
        except requests.exceptions.RequestException as e:
            self.notification.send_message(f"계좌 잔고 조회 실패: {e}")
            return 0
    
    def get_stock_balance(self):
        """
        보유 주식 잔고 조회
        :return: 보유 주식 딕셔너리
        """
        PATH = "uapi/domestic-stock/v1/trading/inquire-balance"
        URL = f"{self.config.URL_BASE}/{PATH}"
        headers = {
            "Content-Type": "application/json", 
            "authorization": f"Bearer {self.config.ACCESS_TOKEN}",
            "appKey": self.config.APP_KEY,
            "appSecret": self.config.APP_SECRET,
            "tr_id": "TTTC8434R"
        }
        params = {
            "CANO": self.config.CANO,
            "ACNT_PRDT_CD": self.config.ACNT_PRDT_CD,
            "AFHR_FLPR_YN": "N",
            "OFL_YN": "",
            "INQR_DVSN": "01",
            "UNPR_DVSN": "01",
            "FUND_STTL_DVSN_CD": "40",
            "FNCG_AMT_AUTO_RDPT_YN": "N"
        }
        
        try:
            res = requests.get(URL, headers=headers, params=params)
            res.raise_for_status()
            output = res.json()['output1']
            stock_dict = {}
            for stock in output:
                if int(stock['bfdy_bltn_qty']) > 0:
                    stock_dict[stock['pdno']] = int(stock['bfdy_bltn_qty'])
            
            self.notification.send_message(f"현재 보유 주식: {stock_dict}")
            return stock_dict
        except requests.exceptions.RequestException as e:
            self.notification.send_message(f"주식 잔고 조회 실패: {e}")
            return {}