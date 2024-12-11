# config/config_manager.py
import os
from dotenv import load_dotenv

class ConfigManager:
    def __init__(self):
        load_dotenv()
        self.access_key = os.getenv("UPBIT_ACCESS_KEY")
        self.secret_key = os.getenv("UPBIT_SECRET_KEY")
        if not self.access_key or not self.secret_key:
            raise ValueError("API keys are missing. Please check your .env file.")

    def get_keys(self):
        return self.access_key, self.secret_key