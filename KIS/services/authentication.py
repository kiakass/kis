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