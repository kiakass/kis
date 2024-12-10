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